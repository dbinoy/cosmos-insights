import pandas as pd
import re
import json
from datetime import datetime, timedelta
from src.utils.db import run_queries
from functools import reduce, lru_cache
from src.utils.performance import monitor_performance

# Global cache for processed compliance data
_compliance_data_cache = {}
_cache_timestamp = None
_cache_duration_minutes = 60  # Cache for 60 minutes

@lru_cache(maxsize=1)
def get_compliance_base_data():
    """
    Fetch and merge compliance case data with global caching
    This is shared across all compliance callbacks for consistency
    """
    global _compliance_data_cache, _cache_timestamp

    try:
        # Check if we have valid cached data
        current_time = datetime.now()
        if (_cache_timestamp and 
            _compliance_data_cache and 
            (current_time - _cache_timestamp).seconds < _cache_duration_minutes * 60):
            # print(f"🎯 Using cached processed compliance data (age: {(current_time - _cache_timestamp).seconds}s)")
            return _compliance_data_cache['merged_df']
        
        # print("📊 Processing fresh compliance case data...")
        
        # Fetch all required tables (these queries are still cached by run_queries)
        queries = {
            "case_details": "SELECT * FROM [consumable].[Fact_CaseDetails]",
            "case_events": "SELECT * FROM [consumable].[Fact_CaseEvents]", 
            "case_notes": "SELECT * FROM [consumable].[Fact_CaseNotes]",
            "case_notices": "SELECT * FROM [consumable].[Fact_CaseNotices]"
        }
        
        result = run_queries(queries, 'compliance', 5)
        
        # Parse JSON columns in Fact_CaseDetails
        case_details_df = result["case_details"].copy()
        
        if 'ViolationName' in case_details_df.columns:
            case_details_df['ViolationName'] = case_details_df['ViolationName'].apply(json.loads)
        if 'ViolationDescription' in case_details_df.columns:
            case_details_df['ViolationDescription'] = case_details_df['ViolationDescription'].apply(json.loads)
        if 'RuleNumber' in case_details_df.columns:
            case_details_df['RuleNumber'] = case_details_df['RuleNumber'].apply(json.loads)
        if 'RuleTitle' in case_details_df.columns:
            case_details_df['RuleTitle'] = case_details_df['RuleTitle'].apply(json.loads)
        if 'CitationFee' in case_details_df.columns:
            case_details_df['CitationFee'] = case_details_df['CitationFee'].apply(json.loads)
        if 'FineType' in case_details_df.columns:
            case_details_df['FineType'] = case_details_df['FineType'].apply(json.loads)
        if 'ReportIds' in case_details_df.columns:
            case_details_df['ReportIds'] = case_details_df['ReportIds'].apply(lambda x: json.loads(x) if pd.notna(x) else [])
            case_details_df.insert(case_details_df.columns.get_loc('ReportIds') + 1, 'NumReportIds', case_details_df['ReportIds'].apply(len))
        
        # Parse JSON columns in other tables
        case_notes_df = result["case_notes"].copy()
        if 'Notes' in case_notes_df.columns:
            case_notes_df['Notes'] = case_notes_df['Notes'].apply(json.loads)
            case_notes_df['NumNotes'] = case_notes_df['Notes'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        case_notices_df = result["case_notices"].copy()
        if 'CaseNotices' in case_notices_df.columns:
            case_notices_df['CaseNotices'] = case_notices_df['CaseNotices'].apply(json.loads)
            case_notices_df['NumCaseNotices'] = case_notices_df['CaseNotices'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        # Group case events by ID
        case_events_df = result["case_events"].copy()
        if not case_events_df.empty:
            grouped_case_events_df = (
                case_events_df
                .drop(columns=['ID'])
                .groupby(case_events_df['ID'])
                .apply(lambda g: g.to_dict(orient='records'))
                .reset_index(name='CaseEvents')
            )
            grouped_case_events_df['NumCaseEvents'] = grouped_case_events_df['CaseEvents'].apply(len)
        else:
            grouped_case_events_df = pd.DataFrame(columns=['ID', 'CaseEvents', 'NumCaseEvents'])
        
        # Merge all dataframes
        dfs = [case_details_df, grouped_case_events_df, case_notices_df, case_notes_df]
        merged_df = reduce(lambda left, right: pd.merge(left, right, on='ID', how='left'), dfs)
        
        # Fill missing values
        list_columns = ['Notes', 'CaseNotices', 'CaseEvents']
        for col in list_columns:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col].apply(lambda x: x if isinstance(x, list) else [])
        
        numeric_columns = ['NumNotes', 'NumCaseNotices', 'NumCaseEvents']
        for col in numeric_columns:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col].fillna(0).astype(int)
        
        # Convert date columns
        date_columns = ['CreatedOn', 'ClosedOn']
        for col in date_columns:
            if col in merged_df.columns:
                merged_df[col] = pd.to_datetime(merged_df[col], errors='coerce')
        
        # Cache the processed result
        _compliance_data_cache['merged_df'] = merged_df
        _cache_timestamp = current_time
        
        # print(f"✅ Processed and cached {len(merged_df)} compliance cases")
        return merged_df
        
    except Exception as e:
        print(f"❌ Error fetching compliance base data: {e}")
        return pd.DataFrame()

def create_normalized_detail_text(detail):
    """
    Normalize and consolidate event detail text for analysis - EXACT COPY from notebook
    """
    
    # Remove extra whitespace and normalize
    detail = detail.replace('\\"', '"')  # Unescape quotes
    detail = detail.replace('\\/', '/')  # Unescape forward slashes
    
    # Remove extra whitespace and normalize
    normalized = re.sub(r'\s+', ' ', detail.strip())
    
    # SECOND: Handle HTML tag scenarios - Use SIMPLE patterns since text is now unescaped
    html_tag_patterns = [
        r'<p[^>]*>.*?</p>',         # <p>content</p>
        r'<div[^>]*>.*?</div>',     # <div>content</div>
        r'<h[1-6][^>]*>.*?</h[1-6]>',  # Any header level: <h1>content</h1>, <h2>content</h2>, etc.
        r'<span[^>]*>.*?</span>',   # <span>content</span>
        r'<strong[^>]*>.*?</strong>', # <strong>content</strong>
        r'<em[^>]*>.*?</em>',       # <em>content</em>
        r'<ul[^>]*>.*?</ul>',       # <ul>content</ul>
        r'<li[^>]*>.*?</li>',       # <li>content</li>
        r'<br\s*/?>',               # <br> or <br/>
        r'</p>',                    # </p> standalone
        r'<p[^>]*>',               # <p> standalone with attributes
        r'<p>',                     # <p> standalone
        r'</div>',                  # </div> standalone
        r'<div[^>]*>',             # <div> standalone with attributes
        r'</h[1-6]>',              # Any closing header tag: </h1>, </h2>, etc.
        r'<h[1-6][^>]*>',          # Any opening header tag with attributes
        r'<h[1-6]>',               # Any simple opening header tag
        r'&[a-zA-Z0-9#]+;',        # HTML entities like &nbsp;, &rsquo;
    ]
    
    # If any HTML tags are present, it's a case note update
    for pattern in html_tag_patterns:
        if re.search(pattern, normalized, re.IGNORECASE | re.DOTALL):
            return 'Case Note updated'
    
    # Handle single hyperlink scenario
    hyperlink_patterns = [
        # Pattern for escaped hyperlinks like: <a href=\"https://...">text</a>
        r'^\s*<a\s+href=\\?"[^"]*\\?"[^>]*>(.*?)<\\?/?a>\s*$',
        # Pattern for normal hyperlinks like: <a href="https://...">text</a>
        r'^\s*<a\s+href="[^"]*"[^>]*>(.*?)</a>\s*$',
        # Pattern for hyperlinks without quotes: <a href=...>text</a>
        r'^\s*<a\s+href=[^>]*>(.*?)</?a>\s*$',
    ]
    
    # Check if the entire detail is just a hyperlink
    for pattern in hyperlink_patterns:
        hyperlink_match = re.match(pattern, normalized, re.IGNORECASE | re.DOTALL)
        if hyperlink_match:
            link_text = hyperlink_match.group(1).strip()
            # Clean up any remaining HTML entities or tags in the link text
            link_text = re.sub(r'&[a-zA-Z0-9]+;', '', link_text)  # Remove HTML entities
            link_text = re.sub(r'<[^>]+>', '', link_text)  # Remove any remaining tags
            return link_text if link_text else 'Link'
        
    # Case and investigation status changes
    case_status_patterns = [
        # Case actions
        (r'.*[Cc]ase [Cc]losed.*', 'Case Closed'),
        (r'.*[Cc]ase [Cc]reated.*', 'Case Created'),
        (r'.*[Cc]ase [Uu]pdated.*', 'Case Updated'),
        (r'.*[Cc]ase [Rr]eopened.*', 'Case Reopened'),
        (r'.*[Cc]ase.*unlinked.*', 'Case unlinked'),
        (r'.*[Cc]ase.*linked.*', 'Case linked'),
        
        # Case Review Status - all variations
        (r'.*[Cc]ase [Rr]eview [Ss]tatus changed.*', 'Case review status changed'),
        (r'.*[Cc]ase [Rr]eview [Uu]pdated.*', 'Case review updated'),
        
        # Investigation patterns - ultra consolidated
        (r'.*[Ii]nvestigation.*relocat.*', 'Investigation relocation to/from another case'),
        (r'.*[Ii]nvestigatio.*[Mm]arked.*', 'Marked for investigation'),
        (r'.*[Ii]nvestigation.*status.*change*', 'Investigation status changed'),
        (r'.*[Ii]nvestigation [Uu]pdated.*', 'Investigation status changed'),
        
        # Notice patterns - consolidate variations
        (r'.*[Nn]otice.*[Dd]efinition.*[Uu]pdated.*', 'NoticeDefinition Updated'),
        (r'.*[Cc]itation.*[Nn]otice.*[Cc]reated.*', 'Citation notice created'),
        (r'.*[Ee]mail.*[Nn]otice.*[Cc]reated.*', 'Email Notice Created'),
        (r'.*[Ii]nquiry.*[Nn]otice.*[Cc]reated.*', 'Inquiry Notice Created'),
        (r'.*[Ii]ncoming.*[Ee]mail.*[Nn]otice.*[Cc]reated.*', 'Incoming Email notice created'),
        (r'.*NoticeType.*Incoming Email.*[Cc]reated.*', 'Incoming Email notice created'),
        (r'.*NoticeType\.Incoming Email.*[Cc]reated.*', 'Incoming Email notice created'),
        (r'.*[Oo]ther.*[Nn]otice.*[Cc]reated.*', 'Other notice created'),
        (r'.*NoticeType.*Other.*[Cc]reated.*', 'Other notice created'),
        (r'.*NoticeType\.Other.*[Cc]reated.*', 'Other notice created'),
        (r'.*[Nn]otice.*[Tt]ranscript.*[Cc]reated.*', 'Notice Transcript created'),
        (r'.*[Oo]ff.*[Ss]ystem.*[Ee]mail.*[Nn]otice.*[Cc]reated.*', 'Off System Email Notice Created'),
        (r'.*[Rr]evised.*[Cc]itation.*[Nn]otice.*[Cc]reated.*', 'Revised Citation Notice Created'),
        (r'.*[Rr]evised.*[Ii]nquiry.*[Nn]otice.*[Cc]reated.*', 'Revised Inquiry Notice Created'),
        (r'.*[Rr]evised.*[Ww]arning.*[Nn]otice.*[Cc]reated.*', 'Revised Warning Notice Created'),
        (r'.*[Ww]arning.*[Nn]otice.*[Cc]reated.*', 'Warning Notice Created'),
        
        # Invoice and payment patterns
        (r'.*[Ii]nvoice.*[Cc]reated.*', 'Invoice created'),
        (r'.*[Ii]nvoice.*[Ss]tatus.*[Cc]hanged.*', 'Invoice status changed'),
        (r'.*[Pp]ayment.*[Cc]reated.*', 'Payment record created'),
        
        # Report patterns
        (r'.*[Aa]ssociated report.*with.*case.*', 'Associated report with the case'),
        (r'.*[Rr]eport.*[Uu]pdated.*', 'Report Updated'),
        (r'.*[Dd]isposition.*[Cc]hanged.*', 'Report disposition changed'),
        (r'.*[Rr]eason changed.*', 'Report reason changed'),
        
        # Communication patterns
        (r'.*[Cc]all.*[Cc]ompliance.*', 'Call compliance'),
        (r'.*[Cc]hat.*[Cc]ompliance.*', 'Chat compliance'),
        (r'.*[Vv]oicemail.*[Cc]ompliance.*', 'Voicemail compliance'),
        
        # Citation and violation patterns
        (r'.*[Cc]itation [Rr]evision.*', 'Citation revision'),
        (r'.*[Cc]ombined [Cc]itation.*', 'Combined citation'),
        (r'.*[Dd]isciplinary.*[Cc]omplaint.*', 'Disciplinary complaint'),
        (r'.*[Gg]eneral.*[Cc]itation.*', 'General Citation'),
        (r'.*[Gg]eneral.*[Ii]nquiry.*', 'General Inquiry'),
        (r'.*[Gg]eneral.*[Ww]arning.*', 'General Warning'),
        
        # Listing modification patterns
        (r'.*[Ll]isting.*[Mm]odification.*', 'Listing modification'),
        
        # System/test entries
        (r'^[Aa][Nn]$', 'testing'),
        (r'^\\n$', 'testing'),
        (r'^[Cc]1 check$', 'C1 check'),
        (r'.*[Tt]est.*', 'testing'),
        (r'.*[Zz]he.*test.*', 'testing'),
        
        # Other patterns
        (r'.*[Nn]ot.*[Aa]pplicable.*', 'Not applicable'),
    ]
    
    # Apply case status patterns
    for pattern, replacement in case_status_patterns:
        if re.match(pattern, normalized, re.IGNORECASE):
            return replacement
                
    # Remove ALL IDs, UUIDs, case numbers, and specific identifiers
    id_cleanup_patterns = [
        # Remove UUIDs (8-4-4-4-12 format) and partial UUIDs
        (r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', ''),
        (r'[a-f0-9]{6,}-[a-f0-9-]{10,}', ''),
        (r'\([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\)', ''),
        # Remove case numbers in various formats
        (r'case: \d+', ''),
        (r'Case \d+', ''),
        (r'from \d+', 'from case'),
        (r'Report \d+', 'Report'),
        # Remove login IDs and member IDs
        (r'Login: [A-Za-z0-9]*', 'Login:'),
        (r'License: [A-Za-z0-9]*', 'License:'),
        # Remove listing IDs and numbers
        (r'for \d{6,}', 'for listing'),
        (r'listing \d{6,}', 'listing'),
        # Remove dollar amounts
        (r'\$\d+(?:\.\d{2})?', '$[Amount]'),
        # Remove standalone numbers (3+ digits)
        (r'\b\d{3,}\b', ''),
        # Remove bracketed content and extra punctuation
        (r'\[ID\]', ''),
        (r'\(\s*\)', ''),
        (r'\(\s*-+\s*\)', ''),
        (r'\([^)]*\)', ''),  # Remove all parenthetical content with IDs
        # Clean up multiple spaces and dashes
        (r'-+', '-'),
        (r'\s+', ' '),
    ]
    
    # Apply ID cleanup
    for pattern, replacement in id_cleanup_patterns:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    
    # Handle truncated and incomplete patterns first (catch "..." endings)
    truncation_patterns = [
        # Truncated Investigation patterns
        (r'7\.8 Failure to Disclose Known Additional Property Owner.*', 'Failure to disclose additional property owner information'),
        (r'Investigation of 11\.5\(e\) Branding in Media.*', 'Case investigation status changed'),
        (r'Investigation of 12\.12 Unauthorized Distribution of MLS.*', 'Case investigation status changed'),
        (r'Investigation of 4\.5 Failure of Participant to Notify.*', 'Case investigation status changed'),
        (r'Investigation of 5\.1\.6 Failure to Comply with.*', 'Case investigation status changed'),
        (r'Investigation of 7\.12 Withdrawal of Listing Prior to.*', 'Case investigation status changed'),
        (r'Investigation of 7\.8 Failure to Disclose Known Additional.*', 'Case investigation status changed'),
        
        # Any other truncated investigation patterns
        (r'Investigation of.*\.\.\.$', 'Case investigation status changed'),
        (r'Investigation of.*: Marked as.*', 'Case investigation status changed'),
        
        # Case member change patterns with truncation
        (r'Case Member changed from Name:.*Login:.*License:.*Name:.*', 'Case Member changed'),
        (r'Case Member changed from Name:.*Login:.*Li\.\.\.', 'Case Member changed'),
        (r'Case Member changed from Name:.*Login:.*Lic\.\.\.', 'Case Member changed'),
        (r'Case Member changed from Name:.*Login:.*Lice\.\.\.', 'Case Member changed'),
    ]
    
    # Apply truncation patterns first
    for pattern, replacement in truncation_patterns:
        if re.match(pattern, normalized, re.IGNORECASE):
            return replacement
    
    # Assignment and member change patterns (ultra-consolidated)
    assignment_patterns = [
        # All From/To patterns become generic assignment change
        (r'From:.*,To:.*', 'Assignment changed from one agent to another'),
        (r'From:,To:.*', 'Assignment changed from one agent to another'),
        
        # All Case Member changed patterns
        (r'Case Member changed from.*to.*', 'Case Member changed'),
        (r'Case Member changed.*', 'Case Member changed'),
        
        # ListingId changes
        (r'ListingId changed from.*to.*', 'ListingId changed'),
        (r'ListingId changed.*', 'ListingId changed'),
    ]
    
    # Apply assignment patterns
    for pattern, replacement in assignment_patterns:
        if re.match(pattern, normalized, re.IGNORECASE):
            return replacement
    
    # Rule-based violations (ultra-consolidated by rule number)
    rule_violation_patterns = [
        # Admin fees
        (r'.*Admin.*Fee.*Charged.*', 'Admin Fee Charged'),
        
        # Citation patterns
        (r'.*Citation.*Corrective Action Required.*', 'Citation Corrective Action Required'),
        (r'.*Citation.*NO Corrective Action Required.*', 'Citation NO Corrective Action Required'),
        
        # Rule 10.x patterns
        (r'.*10\.1.*', 'Failure to Follow  Requirements for Coming Soon '),
        (r'.*10\.2.*', 'Failure to Timely Report'),
        
        # Rule 11.x patterns
        (r'.*11\.5\.1.*', 'Mandatory Submission of Photograph'),
        (r'.*11\.5a.*', 'Improper Media Content'),
        (r'.*11\.5b.*', 'Third-Party Photo'),
        (r'.*11\.5c.*', 'Misrepresentation in Media'),
        (r'.*11\.5d.*[Ww]atermark.*', 'Inadvertent Double Watermarks'),
        (r'.*11\.5d.*[Aa]uthorization.*', 'Use of Media without Prior Authorization'),
        (r'.*11\.5e.*', 'Branding in Media'),
        (r'.*11\.5\(e\).*', 'Branding in Media'),  # Handle parenthetical version
        
        # Rule 12.x patterns
        (r'.*12\.10.*', 'Misleading Advertising and Representations'),
        (r'.*12\.11.*', 'Unauthorized Use of MLS Information'),
        (r'.*12\.12.*', 'Unauthorized Use of MLS Information'),  # Consolidate with 12.11
        (r'.*12\.15.*', 'Unauthorized Reproduction of Confidential Fields'),
        (r'.*12\.22.*', 'Email Address Required'),
        (r'.*12\.5.*', 'Misuse of Remarks'),
        (r'.*12\.7.*', 'Unauthorized Use of Term'),
        (r'.*12\.8.*[Aa]dvertisement.*', 'Unauthorized Advertisement'),
        (r'.*12\.8.*[Cc]ontent.*', 'Unauthorized Listing Content'),
        (r'.*12\.9.*', 'Inadequate Informational Notice'),
        
        # Rule 13.x patterns
        (r'.*13\.2.*', 'Unauthorized Sharing of Lockbox Key'),
        (r'.*13\.7.*', 'Unauthorized Entrance into property'),
        (r'.*13\.9.*', 'Failure to Timely Remove Lockbox'),
        
        # Rule 14.x patterns
        (r'.*14\.4.*[Aa]uto [Ss]old.*', 'Failure to Correct Auto Sold'),
        (r'.*14\.4.*[Vv]iolation.*', 'Failure to Correct violation'),
        (r'.*14\.5.*', 'Modification of Information'),
        
        # Rule 4.x patterns
        (r'.*4\.3.*', 'Failure to notify of termination'),
        (r'.*4\.5.*', 'Failure to notify of termination'),  # Consolidate with 4.3
        
        # Rule 5.x patterns
        (r'.*5\.1\.6.*', 'Citation Corrective Action Required'),  # Consolidate with citation
        
        # Rule 7.x patterns
        (r'.*7\.11.*[Aa]uthorization.*', 'Failure to obtain authorization for changes to listing'),
        (r'.*7\.11.*[Cc]hange.*', 'Failure to change listing information'),
        (r'.*7\.12.*', 'Failure to change listing information'),  # Consolidate withdrawal
        (r'.*7\.15.*', 'No offers of compensation'),
        (r'.*7\.16.*', 'Disclosure of compensation'),
        (r'.*7\.18.*', 'Failure to Comply with Auction Listing Requirements'),
        (r'.*7\.2.*', 'Duplicate Listing Entry'),
        (r'.*7\.20.*', 'Failure to disclose interest in the subject listing'),
        (r'.*7\.3.*', 'Prohibited co-listing'),
        (r'.*7\.6.*', 'Improper Classification of Property Type'),
        (r'.*7\.8.*[Aa]uthorization.*', 'Failure to disclose additional property owner information'),
        (r'.*7\.8.*[Rr]egister.*', 'Failure to register property in MLS'),
        (r'.*7\.8.*[Dd]isclose.*', 'Failure to disclose additional property owner information'),
        (r'.*7\.9.*[Oo]ne.*', 'Citation - One property'),
        (r'.*7\.9.*[Oo]NE.*', 'Citation - One property'),
        (r'.*7\.9.*[Mm]ultiple.*', 'Citation - Multiple properties'),
        (r'.*7\.9.*RLA.*', 'Requesting RLA'),
        
        # Rule 8.x patterns
        (r'.*8\.1.*', 'Failure to obtain seller authorization'),
        (r'.*8\.2.*[Ll]isting.*', 'Failure to provide listing agreement'),
        (r'.*8\.2.*[Dd]ocumentation.*', 'Failure to provide written documentation'),
        (r'.*8\.3.*[Aa]uto [Ss]old.*', 'Auto sold'),
        (r'.*8\.3.*[Ll]isting [Ss]tatus.*', 'Display of inaccurate listing status'),
        (r'.*8\.3.*[Aa]ccurate [Ii]nformation.*', 'Failure to input accurate information'),
        
        # Rule 9.x patterns
        (r'.*9\.1.*', 'Failure to follow showing instructions'),
        (r'.*9\.3.*', 'Misrepresenting availability to show'),
    ]
    
    # Apply rule violation patterns
    for pattern, replacement in rule_violation_patterns:
        if re.match(pattern, normalized, re.IGNORECASE):
            return replacement
    
    # Final cleanup and return
    # Remove extra spaces, clean up punctuation
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    normalized = re.sub(r'^[-\s,:.]+|[-\s,:.]+$', '', normalized)  # Remove leading/trailing punctuation
    normalized = re.sub(r'\s*-\s*-\s*', ' ', normalized)  # Clean up double dashes
    
    # Return cleaned result or fallback
    return normalized if normalized and len(normalized) > 1 else 'Unknown'

@lru_cache(maxsize=1)
@monitor_performance("Event History Creation")
def get_event_history():
    """
    Create event history dataframe from merged case details with normalized event details
    Following the exact notebook approach with caching
    """
    global _compliance_data_cache, _cache_timestamp
    
    try:
        # Check if we have valid cached event history
        current_time = datetime.now()
        if (_cache_timestamp and 
            'event_history_df' in _compliance_data_cache and 
            (current_time - _cache_timestamp).seconds < _cache_duration_minutes * 60):
            return _compliance_data_cache['event_history_df']
        
        # Get merged case details
        merged_df = get_compliance_base_data()
        
        if merged_df.empty or 'CaseEvents' not in merged_df.columns:
            return pd.DataFrame()
        
        # print(f"📊 Processing event history from {len(merged_df)} cases...")
        
        history_records = []
        
        for idx, row in merged_df.iterrows():
            case_id = row['ID']
            case_events = row['CaseEvents']
            
            # Process each event in the case events list
            for event in case_events:
                try:
                    # Extract event details
                    action_date = event.get('ActionDate', '')
                    object_type = event.get('ObjectType', '')
                    event_name = event.get('EventName', '')
                    detail_text = event.get('Detail', '')
                    
                    # Apply normalization to the detail text - EXACT NOTEBOOK FUNCTION
                    normalized_detail = create_normalized_detail_text(detail_text)
                    
                    # Create EventItem as ObjectType + ' - ' + normalized detail
                    event_summary = f"{object_type.replace('Entity', '')} - {normalized_detail}"
                    
                    # Create history record
                    history_record = {
                        'CaseID': case_id,                    
                        'ActionDate': action_date,
                        'ObjectType': object_type,
                        'EventName': event_name,
                        'Detail': detail_text if len(detail_text) < 100 else detail_text[:97] + '...',
                        'EventSummary': event_summary
                    }
                    
                    history_records.append(history_record)
                    
                except Exception as e:
                    continue
            
        # Create the dataframe
        event_history_df = pd.DataFrame(history_records)
        
        # Sort by CaseID and ActionDate for better organization
        if not event_history_df.empty:
            event_history_df = event_history_df.sort_values(['CaseID', 'ActionDate']).reset_index(drop=True)

            # Convert ActionDate to datetime if it's not already
            try:
                event_history_df['ActionDate'] = pd.to_datetime(event_history_df['ActionDate'])
            except:
                print("Warning: Could not convert ActionDate to datetime format")
        
        # Cache the result
        _compliance_data_cache['event_history_df'] = event_history_df
        
        # print(f"✅ Event history dataframe created and cached: {len(event_history_df)} records")
        return event_history_df
        
    except Exception as e:
        print(f"❌ Error creating event history: {e}")
        return pd.DataFrame()

@lru_cache(maxsize=1)
@monitor_performance("Case Flow Analysis")
def get_case_flow():
    """
    Create case flow dataframe following the exact notebook approach
    Merges event history with case details for complete context
    """
    global _compliance_data_cache, _cache_timestamp
    
    try:
        # Check if we have valid cached case flow
        current_time = datetime.now()
        if (_cache_timestamp and 
            'case_flow_df' in _compliance_data_cache and 
            (current_time - _cache_timestamp).seconds < _cache_duration_minutes * 60):
            return _compliance_data_cache['case_flow_df']
        
        # Get event history and merged case data
        event_history_df = get_event_history()
        merged_case_df = get_compliance_base_data()
        
        if event_history_df.empty or merged_case_df.empty:
            return pd.DataFrame()
        
        # Merge event history with case details for complete context
        case_flow_df = event_history_df.merge(
            merged_case_df[['ID', 'CaseNumber', 'MemberName', 'CreatedOn', 'ClosedOn', 
                           'Disposition', 'Status', 'ViolationName', 'NumReportIds']],
            left_on='CaseID', right_on='ID', how='left'
        )
        
        # Convert dates
        case_flow_df['ActionDate'] = pd.to_datetime(case_flow_df['ActionDate'], errors='coerce')
        case_flow_df['CreatedOn'] = pd.to_datetime(case_flow_df['CreatedOn'], errors='coerce')
        case_flow_df['ClosedOn'] = pd.to_datetime(case_flow_df['ClosedOn'], errors='coerce')
        
        # Cache the result
        _compliance_data_cache['case_flow_df'] = case_flow_df
        
        # print(f"✅ Case flow dataframe created and cached: {case_flow_df.shape}")
        return case_flow_df
        
    except Exception as e:
        print(f"❌ Error creating case flow: {e}")
        return pd.DataFrame()

@lru_cache(maxsize=1) 
@monitor_performance("Lifecycle Stage Extraction")
def get_case_flow_with_lifecycle_stages():
    """
    Extract and classify case lifecycle stages from event summaries
    Following EXACT notebook stage patterns
    """
    global _compliance_data_cache, _cache_timestamp
    
    try:
        # Check if we have valid cached lifecycle data
        current_time = datetime.now()
        if (_cache_timestamp and 
            'case_flow_with_stages_df' in _compliance_data_cache and 
            (current_time - _cache_timestamp).seconds < _cache_duration_minutes * 60):
            return _compliance_data_cache['case_flow_with_stages_df']
        
        # Get case flow dataframe
        case_flow_df = get_case_flow()
        
        if case_flow_df.empty:
            return pd.DataFrame()
        
        # Define stage patterns based on EventSummary - EXACT COPY from notebook
        stage_patterns = {
            'Note_Update': [
                'CaseNote - Admin Fee Charged',
                'CaseNote - Auto sold',
                'CaseNote - Branding in Media',
                'CaseNote - C1 check',
                'CaseNote - Call compliance',
                'CaseNote - Case Note updated',
                'CaseNote - Chat compliance',
                'CaseNote - Citation - Multiple properties',
                'CaseNote - Citation - One property',
                'CaseNote - Citation Corrective Action Required',
                'CaseNote - Citation revision',
                'CaseNote - Combined citation',
                'CaseNote - Disciplinary complaint',
                'CaseNote - Disclosure of compensation',
                'CaseNote - Display of inaccurate listing status',
                'CaseNote - Duplicate Listing Entry',
                'CaseNote - Email Address Required',
                'CaseNote - Failure to Comply with Auction Listing Requirements',
                'CaseNote - Failure to Correct Auto Sold',
                'CaseNote - Failure to Correct violation',
                'CaseNote - Failure to Follow Requirements for Coming Soon,',
                'CaseNote - Failure to Timely Remove Lockbox',
                'CaseNote - Failure to Timely Report',
                'CaseNote - Failure to change listing information',
                'CaseNote - Failure to disclose additional property owner information',
                'CaseNote - Failure to follow showing instructions',
                'CaseNote - Failure to input accurate information',
                'CaseNote - Failure to notify of termination',
                'CaseNote - Failure to obtain authorization for changes to listing',
                'CaseNote - Failure to obtain seller authorization',
                'CaseNote - Failure to provide listing agreement',
                'CaseNote - Failure to provide written documentation',
                'CaseNote - Failure to register property in MLS',
                'CaseNote - General Citation',
                'CaseNote - General Inquiry',
                'CaseNote - General Warning',
                'CaseNote - Improper Classification of Property Type',
                'CaseNote - Improper Media Content',
                'CaseNote - Inadequate Informational Notice',
                'CaseNote - Inadvertent Double Watermarks',
                'CaseNote - Investigation relocation to/from another case',
                'CaseNote - Listing modification',
                'CaseNote - Mandatory Submission of Photograph',
                'CaseNote - Misleading Advertising and Representations',
                'CaseNote - Misrepresentation in Media',
                'CaseNote - Misrepresenting availability to show',
                'CaseNote - Misuse of Remarks',
                'CaseNote - Modification of Information',
                'CaseNote - No offers of compensation',
                'CaseNote - Not applicable',
                'CaseNote - Prohibited co-listing',
                'CaseNote - Third-Party Photo',
                'CaseNote - Unauthorized Advertisement',
                'CaseNote - Unauthorized Entrance into property',
                'CaseNote - Unauthorized Listing Content',
                'CaseNote - Unauthorized Reproduction of Confidential Fields',
                'CaseNote - Unauthorized Sharing of Lockbox Key',
                'CaseNote - Unauthorized Use of MLS Information',
                'CaseNote - Unauthorized Use of Term',
                'CaseNote - Unknown',
                'CaseNote - Use of Media without Prior Authorization',
                'CaseNote - Voicemail compliance',
                'CaseNote - testing'
            ],
            'Review_Status_Change': [
                'CaseReview - Case review status changed',
                'CaseReview - Case review updated'
            ],
            'Investigation_Status_Change': [
                'CaseViolation - Investigation status changed'
            ],
            'Investigation_Start': [
                'CaseViolation - Marked for investigation'
            ],
            'Assignee_Change': [
                'ComplianceCase - Assignment changed from one agent to another'
            ],
            'Case_Closure': [
                'ComplianceCase - Case Closed'
            ],
            'Case_Creation': [
                'ComplianceCase - Case Created'
            ],
            'Member_Change': [
                'ComplianceCase - Case Member changed'
            ],
            'Case_Reopening': [
                'ComplianceCase - Case Reopened'
            ],
            'Case_Update': [
                'ComplianceCase - Case Updated'
            ],
            'Listing_Change': [
                'ComplianceCase - ListingId changed'
            ],
            'Test_Stage': [
                'ComplianceCase - testing'
            ],
            'Invoice_Creation': [
                'Invoice - Invoice created'
            ],
            'Invoice_Link': [
                'Invoice - Invoice link'
            ],
            'Invoice_Status_Change': [
                'Invoice - Invoice status changed'
            ],
            'Case_Link': [
                'LinkedCase - Case linked'
            ],
            'Case_Unlink': [
                'LinkedCase - Case unlinked'
            ],
            'Notice_Creation': [
                'NoticeDefinition - Citation notice created',
                'NoticeDefinition - Email Notice Created',
                'NoticeDefinition - Incoming Email notice created',
                'NoticeDefinition - Inquiry Notice Created',
                'NoticeDefinition - Notice Transcript created',
                'NoticeDefinition - NoticeDefinition Updated',
                'NoticeDefinition - Other notice created',
                'NoticeDefinition - Revised Warning Notice Created',
                'NoticeDefinition - Warning Notice Created'
            ],
            'Payment_Invoice_Creation': [
                'Payment - Invoice created'
            ],
            'Payment_Record_Creation': [
                'Payment - Payment record created'
            ],
            'Payment_Record_Update': [
                'Payment - Payment record updated'
            ],
            'Report_Association': [
                'Report - Associated report with the case'
            ],
            'Report_Update': [
                'Report - Report Updated'
            ],
            'Report_Disposition_Change': [
                'Report - Report disposition changed'
            ],
            'Report_Reason_Change': [
                'Report - Report reason changed'
            ]
        }    

        # Create stage mapping
        stage_mapping = {}
        for stage, patterns in stage_patterns.items():
            for pattern in patterns:
                stage_mapping[pattern] = stage
        
        # Apply stage mapping
        case_flow_df['LifecycleStage'] = case_flow_df['EventSummary'].map(stage_mapping)
        case_flow_df['LifecycleStage'] = case_flow_df['LifecycleStage'].fillna('Other')
        
        # Cache the result
        _compliance_data_cache['case_flow_with_stages_df'] = case_flow_df
        
        # print(f"✅ Lifecycle stages extracted and cached")
        return case_flow_df
        
    except Exception as e:
        print(f"❌ Error extracting lifecycle stages: {e}")
        return pd.DataFrame()

@lru_cache(maxsize=1) 
@monitor_performance("Case Progression Analysis")
def get_case_progression_df():
    """
    Analyze case progression through lifecycle stages
    """
    global _compliance_data_cache, _cache_timestamp
    
    try:
        # Check if we have valid cached progression data
        current_time = datetime.now()
        if (_cache_timestamp and 
            'case_progression_df' in _compliance_data_cache and 
            (current_time - _cache_timestamp).seconds < _cache_duration_minutes * 60):
            return _compliance_data_cache['case_progression_df']
        
        # Get case flow with lifecycle stages
        case_flow_df = get_case_flow_with_lifecycle_stages()
        
        if case_flow_df.empty:
            return pd.DataFrame()
        
        # Group by CaseID to get case-level aggregations
        case_groups = case_flow_df.groupby('CaseID')
        
        # Basic case information (take first record for each case)
        case_info = case_flow_df.groupby('CaseID').first()[
            ['CaseNumber', 'MemberName', 'Disposition', 'Status', 'ViolationName', 'CreatedOn', 'ClosedOn']
        ].reset_index()
                
        # Calculate duration metrics
        case_info['CreatedOn'] = pd.to_datetime(case_info['CreatedOn'], errors='coerce')
        case_info['ClosedOn'] = pd.to_datetime(case_info['ClosedOn'], errors='coerce')
        case_info['DurationDays'] = (case_info['ClosedOn'] - case_info['CreatedOn']).dt.days
        
        # Event count metrics
        event_counts = case_groups['EventSummary'].count().rename('TotalEvents').reset_index()
        
        # Stage progression analysis
        stage_progression = case_groups['LifecycleStage'].apply(
            lambda stages: list(dict.fromkeys([s for s in stages if s != 'Other']))
        ).rename('UniqueStages').reset_index()
        
        stage_progression['ProgressionSequence'] = stage_progression['UniqueStages'].apply(
            lambda stages: ' -> '.join(stages)  
        )
        stage_progression['TotalUniqueStages'] = stage_progression['UniqueStages'].apply(len)        

        # Factual stage analysis functions
        def analyze_note_updates(lifecycle_stages):
            """Count Note_Update stages and extract types"""
            note_stages = [s for s in lifecycle_stages if s == 'Note_Update']
            return len(note_stages)
        
        def analyze_review_activity(lifecycle_stages):
            """Analyze review status changes"""
            return {
                'HasReviewActivity': 'Review_Status_Change' in lifecycle_stages,
                'ReviewCount': lifecycle_stages.count('Review_Status_Change')
            }
        
        def analyze_investigation_activity(lifecycle_stages):
            """Analyze investigation stages"""
            has_investigation_start = 'Investigation_Start' in lifecycle_stages
            has_investigation_change = 'Investigation_Status_Change' in lifecycle_stages
            return {
                'HasInvestigationStart': has_investigation_start,
                'HasInvestigationChange': has_investigation_change,
                'InvestigationStartCount': lifecycle_stages.count('Investigation_Start'),
                'InvestigationChangeCount': lifecycle_stages.count('Investigation_Status_Change')
            }
        
        def analyze_assignment_changes(lifecycle_stages):
            """Analyze assignment and member changes"""
            return {
                'HasAssigneeChange': 'Assignee_Change' in lifecycle_stages,
                'HasMemberChange': 'Member_Change' in lifecycle_stages,
                'AssigneeChangeCount': lifecycle_stages.count('Assignee_Change'),
                'MemberChangeCount': lifecycle_stages.count('Member_Change')
            }
        
        def analyze_case_milestones(lifecycle_stages):
            """Analyze general case milestones"""
            return {
                'HasCaseCreation': 'Case_Creation' in lifecycle_stages,
                'HasCaseUpdate': 'Case_Update' in lifecycle_stages,
                'HasCaseReopening': 'Case_Reopening' in lifecycle_stages,
                'HasCaseClosure': 'Case_Closure' in lifecycle_stages,
                'HasListingChange': 'Listing_Change' in lifecycle_stages,
                'CaseUpdateCount': lifecycle_stages.count('Case_Update')
            }
        
        def analyze_financial_activity(lifecycle_stages):
            """Analyze invoice and payment activity"""
            return {
                'HasInvoiceCreation': 'Invoice_Creation' in lifecycle_stages,
                'HasInvoiceLink': 'Invoice_Link' in lifecycle_stages,
                'HasInvoiceStatusChange': 'Invoice_Status_Change' in lifecycle_stages,
                'HasPaymentInvoiceCreation': 'Payment_Invoice_Creation' in lifecycle_stages,
                'HasPaymentRecordCreation': 'Payment_Record_Creation' in lifecycle_stages,
                'HasPaymentRecordUpdate': 'Payment_Record_Update' in lifecycle_stages,
                'InvoiceCreationCount': lifecycle_stages.count('Invoice_Creation'),
                'PaymentRecordCount': lifecycle_stages.count('Payment_Record_Creation') + lifecycle_stages.count('Payment_Record_Update')
            }
        
        def analyze_case_linking(lifecycle_stages):
            """Analyze case linking activity"""
            return {
                'HasCaseLink': 'Case_Link' in lifecycle_stages,
                'HasCaseUnlink': 'Case_Unlink' in lifecycle_stages,
                'CaseLinkCount': lifecycle_stages.count('Case_Link'),
                'CaseUnlinkCount': lifecycle_stages.count('Case_Unlink')
            }
        
        def analyze_report_activity(lifecycle_stages):
            """Analyze report-related activity"""
            return {
                'HasReportAssociation': 'Report_Association' in lifecycle_stages,
                'HasReportUpdate': 'Report_Update' in lifecycle_stages,
                'HasReportDispositionChange': 'Report_Disposition_Change' in lifecycle_stages,
                'HasReportReasonChange': 'Report_Reason_Change' in lifecycle_stages,
                'ReportAssociationCount': lifecycle_stages.count('Report_Association'),
                'ReportUpdateCount': lifecycle_stages.count('Report_Update')
            }
        
        def analyze_notice_creation(lifecycle_stages):
            """Analyze notice creation activity"""
            return {
                'HasNoticeCreation': 'Notice_Creation' in lifecycle_stages,
                'NoticeCreationCount': lifecycle_stages.count('Notice_Creation')
            }

        # Apply analysis functions using pandas operations
        # print("Analyzing note updates...")
        stage_progression['NoteUpdateCount'] = stage_progression['UniqueStages'].apply(analyze_note_updates)

        # print("Analyzing review activity...")
        review_analysis = stage_progression['UniqueStages'].apply(analyze_review_activity)
        review_df = pd.json_normalize(review_analysis)

        # print("Analyzing investigation activity...")
        investigation_analysis = stage_progression['UniqueStages'].apply(analyze_investigation_activity)
        investigation_df = pd.json_normalize(investigation_analysis)

        # print("Analyzing assignment changes...")
        assignment_analysis = stage_progression['UniqueStages'].apply(analyze_assignment_changes)
        assignment_df = pd.json_normalize(assignment_analysis)

        # print("Analyzing case milestones...")
        milestone_analysis = stage_progression['UniqueStages'].apply(analyze_case_milestones)
        milestone_df = pd.json_normalize(milestone_analysis)

        # print("Analyzing financial activity...")
        financial_analysis = stage_progression['UniqueStages'].apply(analyze_financial_activity)
        financial_df = pd.json_normalize(financial_analysis)

        # print("Analyzing case linking...")
        linking_analysis = stage_progression['UniqueStages'].apply(analyze_case_linking)
        linking_df = pd.json_normalize(linking_analysis)

        # print("Analyzing report activity...")
        report_analysis = stage_progression['UniqueStages'].apply(analyze_report_activity)
        report_df = pd.json_normalize(report_analysis)

        # print("Analyzing notice creation...")
        notice_analysis = stage_progression['UniqueStages'].apply(analyze_notice_creation)
        notice_df = pd.json_normalize(notice_analysis)
        
        # Combine all analysis results
        case_progression_df = (case_info
                        .merge(event_counts, on='CaseID', how='left')
                        .merge(stage_progression, on='CaseID', how='left')
                        .reset_index(drop=True)) 

        # Add analysis results
        analysis_dfs = [review_df, investigation_df, assignment_df, milestone_df, 
                    financial_df, linking_df, report_df, notice_df]
        
        for df in analysis_dfs:
            for col in df.columns:
                case_progression_df[col] = df[col].values

        # Summary statistics
        print(f"\n📈 Analysis Results:")
        print(f"   Cases analyzed: {len(case_progression_df):,}")
        print(f"   Average events per case: {case_progression_df['TotalEvents'].mean():.1f}")
        print(f"   Average unique stages per case: {case_progression_df['TotalUniqueStages'].mean():.1f}")
        print(f"   Cases with investigation activity: {case_progression_df['HasInvestigationStart'].sum():,}")
        print(f"   Cases with financial activity: {(case_progression_df['HasInvoiceCreation'] | case_progression_df['HasPaymentRecordCreation']).sum():,}")
        print(f"   Cases with review activity: {case_progression_df['HasReviewActivity'].sum():,}")

        
        # Most common progression patterns
        print(f"\n🎯 Most Common Progression Patterns:")
        common_progressions = case_progression_df['ProgressionSequence'].value_counts().head(10)
        for i, (sequence, count) in enumerate(common_progressions.items(), 1):
            print(f"   {i:2d}. {sequence} ({count} cases)")
        
        # Stage distribution analysis
        print(f"\n📊 Stage Activity Distribution:")
        stage_metrics = {
            'Note Updates': case_progression_df['NoteUpdateCount'].sum(),
            'Review Activities': case_progression_df['ReviewCount'].sum(),
            'Investigation Starts': case_progression_df['InvestigationStartCount'].sum(),
            'Investigation Changes': case_progression_df['InvestigationChangeCount'].sum(),
            'Assignment Changes': case_progression_df['AssigneeChangeCount'].sum(),
            'Member Changes': case_progression_df['MemberChangeCount'].sum(),
            'Case Updates': case_progression_df['CaseUpdateCount'].sum(),
            'Invoice Creations': case_progression_df['InvoiceCreationCount'].sum(),
            'Payment Records': case_progression_df['PaymentRecordCount'].sum(),
            'Notice Creations': case_progression_df['NoticeCreationCount'].sum(),
            'Report Associations': case_progression_df['ReportAssociationCount'].sum()
        }
        
        for metric, count in stage_metrics.items():
            cases_with_metric = case_progression_df[case_progression_df[f"{metric.replace(' ', '').replace('s', '')}Count"] > 0].shape[0] if f"{metric.replace(' ', '').replace('s', '')}Count" in case_progression_df.columns else 0
            print(f"   {metric}: {count:,} total events across cases")


        # Cache the result
        _compliance_data_cache['case_progression_df'] = case_progression_df
        
        # print(f"✅ Case progression dataframe created and cached")
        return case_progression_df
        
    except Exception as e:
        print(f"❌ Error creating case progression: {e}")
        return pd.DataFrame()


def invalidate_compliance_cache():
    """Manually invalidate the cache if needed"""
    global _compliance_data_cache, _cache_timestamp
    _compliance_data_cache = {}
    _cache_timestamp = None
    get_compliance_base_data.cache_clear()
    get_event_history.cache_clear()
    get_case_flow.cache_clear()
    get_case_flow_with_lifecycle_stages.cache_clear()
    get_case_progression_df.cache_clear()
    # print("🗑️ All compliance data caches invalidated")

@monitor_performance("Compliance Filter Application")
def apply_compliance_filters(df, filter_selections):
    """Apply compliance-specific filters - standardized across all callbacks"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # Apply date filter
    if filter_selections.get('Day_From') and filter_selections.get('Day_To'):
        date_from = pd.to_datetime(filter_selections['Day_From'])
        date_to = pd.to_datetime(filter_selections['Day_To'])
        if 'CreatedOn' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['CreatedOn'] >= date_from) &
                (filtered_df['CreatedOn'] <= date_to)
            ]
    
    # Apply Disposition filter
    if filter_selections.get('Disposition'):
        disposition_list = [d.strip().strip("'") for d in filter_selections['Disposition'].split(',')]
        filtered_df = filtered_df[filtered_df['Disposition'].isin(disposition_list)]
    
    # Apply AssignedUser filter
    if filter_selections.get('AssignedUser'):
        user_list = [u.strip().strip("'") for u in filter_selections['AssignedUser'].split(',')]
        filtered_df = filtered_df[filtered_df['AssignedUser'].isin(user_list)]
    
    # Apply ViolationName filter (list column)
    if filter_selections.get('ViolationName'):
        violation_list = [v.strip().strip("'") for v in filter_selections['ViolationName'].split(',')]
        filtered_df = filtered_df[filtered_df['ViolationName'].apply(
            lambda x: any(item in violation_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply RuleNumber filter (list column)
    if filter_selections.get('RuleNumber'):
        rule_list = [r.strip().strip("'") for r in filter_selections['RuleNumber'].split(',')]
        filtered_df = filtered_df[filtered_df['RuleNumber'].apply(
            lambda x: any(item in rule_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply RuleTitle filter (list column)
    if filter_selections.get('RuleTitle'):
        title_list = [t.strip().strip("'") for t in filter_selections['RuleTitle'].split(',')]
        filtered_df = filtered_df[filtered_df['RuleTitle'].apply(
            lambda x: any(item in title_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply CitationFee filter (list column)
    if filter_selections.get('CitationFee'):
        fee_list = [f.strip().strip("'") for f in filter_selections['CitationFee'].split(',')]
        filtered_df = filtered_df[filtered_df['CitationFee'].apply(
            lambda x: any(item in fee_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply FineType filter (list column)
    if filter_selections.get('FineType'):
        type_list = [t.strip().strip("'") for t in filter_selections['FineType'].split(',')]
        filtered_df = filtered_df[filtered_df['FineType'].apply(
            lambda x: any(item in type_list for item in x) if isinstance(x, list) else False
        )]
    
    # Apply NumReports filter
    if filter_selections.get('NumReports'):
        num_list = [int(n.strip()) for n in filter_selections['NumReports'].split(',')]
        filtered_df = filtered_df[filtered_df['NumReportIds'].isin(num_list)]
    
    return filtered_df

@monitor_performance("Outstanding Issues Classification")
def classify_case_severity(df):
    """
    Classify compliance cases by severity level based on violation types and additional factors
    
    Returns DataFrame with additional columns:
    - BaseSeverity: Base severity from violation type
    - FinalSeverity: Final severity after applying multipliers
    - SeverityReason: Reason for severity classification
    - IsOutstanding: Boolean indicating if case is outstanding (unresolved)
    """
    if df.empty:
        return df
    
    df_classified = df.copy()
    
    def get_base_severity_from_violations(violation_list):
        """Classify base severity from violation types"""
        if not isinstance(violation_list, list) or len(violation_list) == 0:
            return "RESOLVED", "No violations"
        
        # Get first non-null violation
        violation = None
        for v in violation_list:
            if v is not None and str(v).strip():
                violation = v
                break
        
        if not violation:
            return "DATA_ISSUE", "Null violation data"
        
        # CRITICAL - Immediate Action Required
        if violation in ['Citation', 'Citation: Unresolved', 'Combined Citation', 
                        'Disciplinary Complaint', 'Disciplinary Complaint Upheld']:
            return "CRITICAL", f"Active enforcement: {violation}"
        
        # HIGH - Urgent (Within 7 Days)
        elif violation in ['Investigation Created', 'Escalated', 'Warning', 'Violation Override']:
            return "HIGH", f"Investigation/escalation: {violation}"
        
        # MEDIUM - Standard Priority (Within 30 Days) 
        elif violation in ['AOR/MLS Referral', 'Transferred to OM/DB', 'Modification']:
            return "MEDIUM", f"Administrative action: {violation}"
        
        # LOW - Routine (Standard Timeline)
        elif violation in ['Call', 'Chat', 'Left Voicemail']:
            return "LOW", f"Communication activity: {violation}"
        
        # RESOLVED/CLOSED - No Action Required
        elif violation in ['Corrected', 'Corrected Prior to Review', 'Citation - Dismissed by review panel',
                          'Disciplinary Complaint Dismissed', 'No Violation', 'Duplicate', 
                          'Aged Report', 'Unable to Verify', 'Withdrawn']:
            return "RESOLVED", f"Case resolved: {violation}"
        
        # DATA ISSUES
        elif violation in ['Null', None, ''] or str(violation).strip() == '':
            return "DATA_ISSUE", "Missing violation data"
        
        else:
            return "MEDIUM", f"Other violation: {violation}"
    
    def apply_severity_multipliers(base_severity, row):
        """Apply multipliers based on case characteristics"""
        severity_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        level_names = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
        
        if base_severity in ["RESOLVED", "DATA_ISSUE"]:
            return base_severity, []
        
        current_level = severity_levels.get(base_severity, 2)
        multipliers_applied = []
        
        # Unassigned cases: +1 severity level
        if pd.isna(row.get('AssignedUser')) or str(row.get('AssignedUser', '')).strip() == '':
            current_level = min(current_level + 1, 4)
            multipliers_applied.append("Unassigned (+1)")
        
        # Age factor: Cases open > 10 days get +1 severity level
        if 'CreatedOn' in row and pd.notna(row['CreatedOn']):
            try:
                created_date = pd.to_datetime(row['CreatedOn'])
                days_open = (pd.Timestamp.now() - created_date).days
                if days_open > 10:
                    current_level = min(current_level + 1, 4)
                    multipliers_applied.append(f"Aging {days_open} days (+1)")
            except:
                pass
        
        final_severity = level_names.get(current_level, base_severity)
        return final_severity, multipliers_applied
    
    def is_case_outstanding(row):
        """Determine if case is outstanding (unresolved)"""
        # Check disposition first
        disposition = row.get('Disposition', '')
        if disposition and str(disposition).lower() in ['closed', 'resolved', 'complete']:
            return False
        
        # Check status
        status = row.get('Status', '')
        if status and str(status).lower() in ['closed', 'resolved', 'complete']:
            return False
        
        # Check violation types for resolved cases
        violation_list = row.get('ViolationName', [])
        if isinstance(violation_list, list) and len(violation_list) > 0:
            first_violation = violation_list[0] if violation_list[0] is not None else None
            if first_violation in ['Corrected', 'Corrected Prior to Review', 'Citation - Dismissed by review panel',
                                 'Disciplinary Complaint Dismissed', 'No Violation', 'Duplicate', 
                                 'Aged Report', 'Unable to Verify', 'Withdrawn']:
                return False
        
        # If none of the above, consider it outstanding
        return True
    
    # Apply classifications
    severity_data = df_classified.apply(
        lambda row: get_base_severity_from_violations(row.get('ViolationName', [])), axis=1
    )
    
    df_classified['BaseSeverity'] = [s[0] for s in severity_data]
    df_classified['BaseSeverityReason'] = [s[1] for s in severity_data]
    
    # Apply multipliers
    final_severity_data = df_classified.apply(
        lambda row: apply_severity_multipliers(row['BaseSeverity'], row), axis=1
    )
    
    df_classified['FinalSeverity'] = [s[0] for s in final_severity_data]
    df_classified['SeverityMultipliers'] = [s[1] for s in final_severity_data]
    
    # Create comprehensive severity reason
    df_classified['SeverityReason'] = df_classified.apply(
        lambda row: f"{row['BaseSeverityReason']}" + 
                   (f" | Multipliers: {', '.join(row['SeverityMultipliers'])}" if row['SeverityMultipliers'] else ""), 
        axis=1
    )
    
    # Determine outstanding status
    df_classified['IsOutstanding'] = df_classified.apply(is_case_outstanding, axis=1)
    
    # Calculate days open
    df_classified['DaysOpen'] = df_classified.apply(
        lambda row: (pd.Timestamp.now() - pd.to_datetime(row['CreatedOn'])).days 
        if pd.notna(row.get('CreatedOn')) else 0, axis=1
    )
    
    return df_classified

@monitor_performance("Outstanding Issues Data Preparation")
def prepare_outstanding_issues_data(df, view_state="severity"):
    """
    Prepare outstanding issues data based on view state
    Only includes cases that are truly outstanding (unresolved)
    """
    if df.empty:
        return pd.DataFrame(), {}
    
    # First classify all cases
    classified_df = classify_case_severity(df)
    
    # Filter to only outstanding cases
    outstanding_df = classified_df[classified_df['IsOutstanding'] == True].copy()
    
    if outstanding_df.empty:
        return pd.DataFrame(), {'total_cases': 0, 'outstanding_cases': 0}
    
    # Prepare data based on view state
    if view_state == "severity":
        # Group by final severity level
        status_counts = outstanding_df['FinalSeverity'].value_counts().reset_index()
        status_counts.columns = ['Category', 'Count']
        
        # Ensure proper ordering (CRITICAL -> HIGH -> MEDIUM -> LOW -> DATA_ISSUE)
        severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'DATA_ISSUE']
        status_counts['SortOrder'] = status_counts['Category'].map(
            {sev: i for i, sev in enumerate(severity_order)}
        ).fillna(99)
        status_counts = status_counts.sort_values('SortOrder').drop('SortOrder', axis=1).reset_index(drop=True)
        
    elif view_state == "age":
        # Group by age buckets
        def categorize_age(days):
            if days <= 7:
                return "≤7 days (Fresh)"
            elif days <= 30:
                return "8-30 days (Recent)"
            elif days <= 90:
                return "31-90 days (Aging)"
            else:
                return ">90 days (Stale)"
        
        outstanding_df['AgeCategory'] = outstanding_df['DaysOpen'].apply(categorize_age)
        status_counts = outstanding_df['AgeCategory'].value_counts().reset_index()
        status_counts.columns = ['Category', 'Count']
        
        # Sort by age order
        age_order = ["≤7 days (Fresh)", "8-30 days (Recent)", "31-90 days (Aging)", ">90 days (Stale)"]
        status_counts['SortOrder'] = status_counts['Category'].map(
            {age: i for i, age in enumerate(age_order)}
        ).fillna(99)
        status_counts = status_counts.sort_values('SortOrder').drop('SortOrder', axis=1).reset_index(drop=True)
        
    elif view_state == "assignment":
        # Group by assignment status
        def categorize_assignment(assigned_user):
            if pd.isna(assigned_user) or str(assigned_user).strip() == '':
                return "🚨 Unassigned"
            else:
                return f"👤 {str(assigned_user).strip()}"
        
        outstanding_df['AssignmentCategory'] = outstanding_df['AssignedUser'].apply(categorize_assignment)
        status_counts = outstanding_df['AssignmentCategory'].value_counts().reset_index()
        status_counts.columns = ['Category', 'Count']
        
        # Sort with unassigned first (highest priority)
        status_counts['IsUnassigned'] = status_counts['Category'].str.contains('🚨 Unassigned')
        status_counts = status_counts.sort_values(['IsUnassigned', 'Count'], ascending=[False, False]).drop('IsUnassigned', axis=1).reset_index(drop=True)
        
    elif view_state == "violation":
        # Group by violation type (first violation)
        def get_first_violation(violation_list):
            if isinstance(violation_list, list) and len(violation_list) > 0:
                return violation_list[0] if violation_list[0] is not None else "No Violation"
            return "No Violation"
        
        outstanding_df['FirstViolation'] = outstanding_df['ViolationName'].apply(get_first_violation)
        status_counts = outstanding_df['FirstViolation'].value_counts().reset_index()
        status_counts.columns = ['Category', 'Count']
        
        # Sort by count descending
        status_counts = status_counts.sort_values('Count', ascending=False).reset_index(drop=True)
    
    # Calculate summary stats
    total_cases = len(df)
    outstanding_cases = len(outstanding_df)
    
    # Severity breakdown
    severity_breakdown = outstanding_df['FinalSeverity'].value_counts().to_dict()
    
    # Assignment stats
    unassigned_count = len(outstanding_df[
        outstanding_df['AssignedUser'].isna() | 
        (outstanding_df['AssignedUser'].astype(str).str.strip() == '')
    ])
    
    # Age stats
    aging_count = len(outstanding_df[outstanding_df['DaysOpen'] > 30])
    stale_count = len(outstanding_df[outstanding_df['DaysOpen'] > 90])
    
    summary_stats = {
        'total_cases': total_cases,
        'outstanding_cases': outstanding_cases,
        'outstanding_percentage': (outstanding_cases / total_cases * 100) if total_cases > 0 else 0,
        'critical_cases': severity_breakdown.get('CRITICAL', 0),
        'high_cases': severity_breakdown.get('HIGH', 0),
        'unassigned_cases': unassigned_count,
        'aging_cases': aging_count,
        'stale_cases': stale_count,
        'avg_days_open': outstanding_df['DaysOpen'].mean() if not outstanding_df.empty else 0
    }
    
    return status_counts, summary_stats

@monitor_performance("Recent Activities Data Preparation")
def prepare_recent_activities_data(df, timeframe="30d", activity_type="all"):
    """
    Prepare recent activities data for visualization - Now uses cached event history with lifecycle stages
    
    Parameters:
    df: Merged case details dataframe (for filtering only)
    timeframe: "7d", "30d", "90d", "6m"
    activity_type: "all", "investigations", "communications", "notices", etc.
    """
    if df.empty:
        return pd.DataFrame(), {}
    
    # Get processed case flow with lifecycle stages from cache (heavy processing already done)
    case_flow_df = get_case_flow_with_lifecycle_stages()
    
    if case_flow_df.empty:
        return pd.DataFrame(), {'total_activities': 0, 'date_range': ''}
    
    # Filter case flow to match the filtered cases (if filters are applied)
    case_ids_in_filtered_df = set(df['ID'].tolist())
    recent_events = case_flow_df[case_flow_df['CaseID'].isin(case_ids_in_filtered_df)].copy()
    
    if recent_events.empty:
        return pd.DataFrame(), {'total_activities': 0, 'date_range': ''}
    
    # Filter by timeframe
    end_date = pd.Timestamp.now()
    
    timeframe_days = {
        '7d': 7, '30d': 30, '90d': 90, '6m': 180
    }
    
    days = timeframe_days.get(timeframe, 30)
    start_date = end_date - pd.Timedelta(days=days)
    
    # Filter events within timeframe
    recent_events = recent_events[
        (recent_events['ActionDate'] >= start_date) &
        (recent_events['ActionDate'] <= end_date)
    ].copy()
    
    if recent_events.empty:
        return pd.DataFrame(), {
            'total_activities': 0, 'date_range': f'{start_date.date()} to {end_date.date()}',
            'timeframe_label': f'Last {days} days'
        }
    
    # Filter by activity type if specified (LifecycleStage is now available)
    if activity_type != "all":
        activity_filters = {
            'investigations': ['Investigation_Start', 'Investigation_Status_Change'],
            'communications': ['Note_Update'],  # Communication patterns are in Note_Update
            'notices': ['Notice_Creation'],
            'case_management': ['Case_Creation', 'Case_Update', 'Case_Closure', 'Case_Reopening'],
            'financial': ['Invoice_Creation', 'Invoice_Status_Change', 'Payment_Invoice_Creation', 'Payment_Record_Creation', 'Payment_Record_Update'],
            'reports': ['Report_Association', 'Report_Update', 'Report_Disposition_Change', 'Report_Reason_Change']
        }
        
        if activity_type in activity_filters:
            recent_events = recent_events[
                recent_events['LifecycleStage'].isin(activity_filters[activity_type])
            ]
    
    # Prepare summary statistics
    summary_stats = {
        'total_activities': len(recent_events),
        'unique_cases': recent_events['CaseID'].nunique(),
        'date_range': f'{start_date.date()} to {end_date.date()}',
        'timeframe_label': f'Last {days} days',
        'daily_average': len(recent_events) / days,
        'most_active_day': recent_events['ActionDate'].dt.date.value_counts().index[0] if not recent_events.empty else None,
        'stage_breakdown': recent_events['LifecycleStage'].value_counts().to_dict()
    }
    
    return recent_events, summary_stats