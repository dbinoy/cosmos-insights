from dash import callback, ctx, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from src.utils.compliance_data import get_compliance_base_data, apply_compliance_filters
from src.utils.performance import monitor_performance, monitor_chart_performance
import numpy as np
from collections import Counter
import copy

def register_compliance_incident_analysis_callbacks(app):
    """Register incident analysis callbacks"""
    
    @monitor_chart_performance("Incident Analysis Chart")
    def create_incident_analysis_chart(filtered_df, view_type):
        """Create incident analysis chart based on view type"""
        
        if filtered_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No incident data found for the selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=14, color="gray")
            )
            fig.update_layout(
                title={'text': "Incident Analysis - No Data", 'x': 0.5, 'xanchor': 'center'},
                height=400
            )
            return fig
        
        if view_type == "category":
            # Group violations into logical categories
            def categorize_rule_violation(rule_list):
                """Categorize violations by business-meaningful rule categories based on actual rule content"""
                if not isinstance(rule_list, list) or len(rule_list) == 0:
                    return "Administrative & Process"
                
                # Get first rule number/title
                first_rule = rule_list[0] if rule_list[0] is not None else ""
                if not first_rule:
                    return "Administrative & Process"
                
                rule_str = str(first_rule).upper()
                
                # Citation and General Categories (most common patterns)
                if any(keyword in rule_str for keyword in ['GENERAL', 'CITATION', 'WARNING', 'INQUIRY', 'COMBINED', 'DISCIPLINARY']):
                    if 'DISCIPLINARY' in rule_str:
                        return "Disciplinary Actions"
                    elif 'COMBINED' in rule_str:
                        return "Combined Violations"
                    elif 'CITATION' in rule_str and 'GENERAL' in rule_str:
                        return "General Citations"
                    elif 'WARNING' in rule_str:
                        return "Warnings & Inquiries"
                    elif 'INQUIRY' in rule_str:
                        return "Warnings & Inquiries"
                    elif '1%' in rule_str or 'CITATION' in rule_str:
                        return "Standard Citations"
                    else:
                        return "General Compliance"
                
                # Communication Categories
                if any(keyword in rule_str for keyword in ['CALL', 'CHAT', 'VOICEMAIL']):
                    return "Customer Service & Communication"
                
                # Listing Management (7.x rules)
                if rule_str.startswith('7.') or 'LISTING' in rule_str:
                    if any(keyword in rule_str for keyword in ['DUPLICATE', 'CO-LISTING', 'PROHIBITED']):
                        return "Listing Registration & Setup"
                    elif any(keyword in rule_str for keyword in ['COMPENSATION', 'COMMISSION', 'DISCLOSURE']):
                        return "Commission & Disclosure"
                    elif any(keyword in rule_str for keyword in ['AUTHORIZATION', 'PERMISSION', 'AGREEMENT']):
                        return "Authorization & Documentation"
                    elif any(keyword in rule_str for keyword in ['WITHDRAWAL', 'EXPIRATION', 'RENEWAL', 'STATUS']):
                        return "Listing Status Management"
                    elif any(keyword in rule_str for keyword in ['CLASSIFICATION', 'TYPE', 'REO', 'AUCTION']):
                        return "Property Classification"
                    else:
                        return "Listing Management"
                
                # Documentation and Authorization (8.x rules)
                if rule_str.startswith('8.') or any(keyword in rule_str for keyword in ['DOCUMENTATION', 'AGREEMENT', 'AUTHORIZATION']):
                    if 'AUTO SOLD' in rule_str:
                        return "Auto Sold & Status Updates"
                    elif any(keyword in rule_str for keyword in ['INACCURATE', 'INCOMPLETE', 'ACCURATE INFORMATION']):
                        return "Data Accuracy & Integrity"
                    else:
                        return "Authorization & Documentation"
                
                # Showing and Access (9.x rules)
                if rule_str.startswith('9.') or any(keyword in rule_str for keyword in ['SHOWING', 'INSPECT', 'BUYER AGREEMENT']):
                    return "Property Showing & Access"
                
                # Status Changes and Reporting (10.x rules)
                if rule_str.startswith('10.') or any(keyword in rule_str for keyword in ['COMING SOON', 'STATUS CHANGE', 'TIMELY REPORT']):
                    return "Status Reporting & Timing"
                
                # Media and Photography (11.x rules)
                if rule_str.startswith('11.') or any(keyword in rule_str for keyword in ['PHOTO', 'MEDIA', 'RENDERING', 'WATERMARK', 'BRANDING']):
                    if any(keyword in rule_str for keyword in ['BRANDING', 'WATERMARK']):
                        return "Media Branding & Attribution"
                    elif any(keyword in rule_str for keyword in ['THIRD-PARTY', 'AUTHORIZATION', 'PERMISSION']):
                        return "Media Authorization & Rights"
                    elif any(keyword in rule_str for keyword in ['CONTENT', 'MISREPRESENTATION', 'UNTRUTHFULNESS']):
                        return "Media Content Standards"
                    else:
                        return "Photography & Media"
                
                # MLS Usage and Advertising (12.x rules)
                if rule_str.startswith('12.') or any(keyword in rule_str for keyword in ['MLS', 'ADVERTISING', 'UNAUTHORIZED USE', 'DISTRIBUTION']):
                    if any(keyword in rule_str for keyword in ['REMARKS', 'PUBLIC REMARKS', 'OTHER REMARKS']):
                        return "MLS Remarks & Comments"
                    elif any(keyword in rule_str for keyword in ['NEIGHBORHOOD MARKET', 'ADVERTISEMENT OF LISTING']):
                        return "Marketing & Advertising"
                    elif any(keyword in rule_str for keyword in ['UNAUTHORIZED USE', 'UNAUTHORIZED DISTRIBUTION', 'PASSCODES']):
                        return "MLS Data Security & Usage"
                    elif any(keyword in rule_str for keyword in ['FALSE', 'MISLEADING', 'INFORMATIONAL NOTICE']):
                        return "Advertising Standards"
                    elif 'EMAIL' in rule_str:
                        return "Contact Information Management"
                    else:
                        return "MLS Usage & Compliance"
                
                # Lockbox and Property Access (13.x rules)
                if rule_str.startswith('13.') or any(keyword in rule_str for keyword in ['LOCKBOX', 'PROPERTY ACCESS', 'ENTRANCE']):
                    return "Lockbox & Property Security"
                
                # Corrections and Compliance (14.x rules)
                if rule_str.startswith('14.') or any(keyword in rule_str for keyword in ['FAILURE TO CORRECT', 'MODIFICATION']):
                    return "Compliance & Corrections"
                
                # Membership and Participation (4.x, 5.x rules)
                if rule_str.startswith(('4.', '5.')) or any(keyword in rule_str for keyword in ['PARTICIPANT', 'SUBSCRIBER', 'TERMINATION', 'ADDITION', 'LICENSEE']):
                    if 'CERTIFICATION' in rule_str or 'NONUSE' in rule_str:
                        return "Fee Management & Certification"
                    else:
                        return "Membership & User Management"
                
                # Technology and Internet Usage (19.x rules)
                if rule_str.startswith('19.') or any(keyword in rule_str for keyword in ['INTERNET', 'IDX', 'VOW']):
                    return "Internet & Technology Compliance"
                
                # DRE/OREA and Legal (regulatory compliance)
                if any(keyword in rule_str for keyword in ['DRE', 'OREA', 'ADVERSE ACTION']):
                    return "Regulatory Compliance"
                
                # Not Applicable or Administrative
                if 'NOT APPLICABLE' in rule_str or 'N/A' in rule_str:
                    return "Administrative & Process"
                
                # Special handling for "Other" in rule titles
                if 'OTHER' in rule_str:
                    if 'REMARKS' in rule_str or 'MEDIA' in rule_str:
                        return "MLS Remarks & Comments"
                    else:
                        return "Miscellaneous Violations"
                
                # Modification-related
                if 'MODIFICATION' in rule_str:
                    return "Data Modifications & Updates"
                
                # Default fallback - use rule number pattern if available
                if rule_str.startswith(('0', '99')):
                    return "General Compliance"
                
                # Final fallback for truly unknown categories
                return "Uncategorized Violations"
            
            # Categorize violations
            df_analysis = filtered_df.copy()
            df_analysis['ViolationCategory'] = df_analysis['RuleNumber'].apply(categorize_rule_violation)
            
            # Count by category
            category_counts = df_analysis['ViolationCategory'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Count']
            
            # Create horizontal bar chart
            colors = px.colors.qualitative.Set1[:len(category_counts)]
            
            fig = go.Figure(data=[go.Bar(
                y=category_counts['Category'],
                x=category_counts['Count'],
                orientation='h',
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{y}</b><br>Cases: %{x}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                customdata=category_counts['Count'] / category_counts['Count'].sum() * 100,
                text=category_counts['Count'],
                textposition='inside'
            )])
            
            fig.update_layout(
                title={
                    'text': f"Compliance Incidents by Category ({category_counts['Count'].sum():,} Total Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Number of Cases",
                yaxis_title="",
                height=400,
                margin={'l': 200, 'r': 50, 't': 80, 'b': 50}
            )
            
        elif view_type == "rule":
            # Analyze by specific rule number families
            def categorize_detailed_rule(rule_list):
                """Detailed rule categorization based on specific rule families and content"""
                if not isinstance(rule_list, list) or len(rule_list) == 0:
                    return "Administrative"
                
                first_rule = str(rule_list[0]) if rule_list[0] is not None else ""
                if not first_rule:
                    return "Administrative"
                
                rule_str = first_rule.upper()
                
                # General and Citation Categories (0.x and special codes)
                if rule_str.startswith('0') or any(keyword in rule_str for keyword in ['GENERAL', '1% CITATION']):
                    if 'DISCIPLINARY' in rule_str:
                        return "Disciplinary Complaints"
                    elif 'COMBINED' in rule_str:
                        return "Combined Citations"
                    elif 'WARNING' in rule_str:
                        return "General Warnings"
                    elif 'INQUIRY' in rule_str:
                        return "General Inquiries"
                    elif 'CITATION' in rule_str and 'AGENT BASED' in rule_str:
                        return "Agent-Based Citations"
                    elif 'CITATION' in rule_str or '1%' in rule_str:
                        return "Standard Citations"
                    else:
                        return "General Compliance"
                
                # Communication Categories
                if any(keyword in rule_str for keyword in ['CALL', 'CHAT', 'VOICEMAIL']):
                    return "Customer Service Communications"
                
                # Membership and Participation (4.x, 5.x)
                elif first_rule.startswith('4.3'):
                    return "4.3 - Clerical User Management"
                elif first_rule.startswith('4.5'):
                    return "4.5 - Licensee Management"
                elif first_rule.startswith('5.1.6'):
                    return "5.1.6 - Nonuse Certification & Fees"
                elif first_rule.startswith(('4.', '5.')):
                    return "4-5.x - Membership Rules"
                
                # Listing Management (7.x) - Comprehensive breakdown
                elif first_rule.startswith('7.2'):
                    return "7.2 - Duplicate Listings & Disclosure"
                elif first_rule.startswith('7.3'):
                    return "7.3 - Co-Listing Restrictions"
                elif first_rule.startswith('7.6'):
                    return "7.6 - Property Type Classification"
                elif first_rule.startswith('7.8'):
                    return "7.8 - MLS Registration & Owner Info"
                elif first_rule.startswith('7.9'):
                    if 'RLA' in rule_str:
                        return "7.9 - RLA Requests"
                    else:
                        return "7.9 - Citation Processing"
                elif first_rule.startswith('7.11'):
                    return "7.11 - Authorization & Updates"
                elif first_rule.startswith('7.12'):
                    return "7.12 - Listing Withdrawal"
                elif first_rule.startswith('7.15'):
                    return "7.15 - Compensation Offers"
                elif first_rule.startswith('7.16'):
                    return "7.16 - Compensation Disclosure"
                elif first_rule.startswith('7.18'):
                    if 'AUCTION' in rule_str:
                        return "7.18.1 - Auction Requirements"
                    elif 'CONSTRUCTION' in rule_str:
                        return "7.18.4 - New Construction"
                    else:
                        return "7.18 - Special Listing Types"
                elif first_rule.startswith('7.20'):
                    return "7.20 - Interest Disclosure"
                elif first_rule.startswith('7.22'):
                    return "7.22 - Listing Renewal & Expiration"
                elif first_rule.startswith('7.25'):
                    return "7.25 - Dual/Variable Commission"
                elif first_rule.startswith('7.27'):
                    return "7.27 - REO Status Disclosure"
                elif first_rule.startswith('7.9.1'):
                    return "7.9.1 - No-Cooperation Listings"
                elif first_rule.startswith('7.'):
                    return "7.x - Other Listing Rules"
                
                # Documentation & Authorization (8.x)
                elif first_rule.startswith('8.1'):
                    return "8.1 - Seller Authorization"
                elif first_rule.startswith('8.2'):
                    return "8.2 - Documentation Requests"
                elif first_rule.startswith('8.3'):
                    if 'AUTO SOLD' in rule_str:
                        return "8.3 - Auto Sold Issues"
                    elif 'CONCESSIONS' in rule_str:
                        return "8.3 - Concessions & Accuracy"
                    elif 'INACCURATE' in rule_str or 'INCOMPLETE' in rule_str:
                        return "8.3 - Information Accuracy"
                    else:
                        return "8.3 - Data Input & Status"
                elif first_rule.startswith('8.'):
                    return "8.x - Documentation Rules"
                
                # Showing & Access (9.x)
                elif first_rule.startswith('9.1'):
                    return "9.1 - Showing Instructions & Agreements"
                elif first_rule.startswith('9.3'):
                    return "9.3 - Availability & Coming Soon"
                elif first_rule.startswith('9.9'):
                    return "9.9 - Physical Presence Requirements"
                elif first_rule.startswith('9.'):
                    return "9.x - Showing Rules"
                
                # Status Changes & Reporting (10.x)
                elif first_rule.startswith('10.1'):
                    return "10.1 - Coming Soon Requirements"
                elif first_rule.startswith('10.2'):
                    return "10.2 - Status Change Reporting"
                elif first_rule.startswith('10.4'):
                    return "10.4 - Cancellation Reporting"
                elif first_rule.startswith('10.5'):
                    return "10.5 - Seller Refusal Reporting"
                elif first_rule.startswith('10.'):
                    return "10.x - Status & Reporting Rules"
                
                # Media & Photography (11.x)
                elif first_rule.startswith('11.5.1'):
                    return "11.5.1 - Mandatory Photos"
                elif first_rule.startswith('11.5a'):
                    return "11.5a - Media Content Standards"
                elif first_rule.startswith('11.5b'):
                    return "11.5b - Third-Party Photos"
                elif first_rule.startswith('11.5c'):
                    return "11.5c - Media Truthfulness"
                elif first_rule.startswith('11.5d'):
                    if 'WATERMARK' in rule_str:
                        return "11.5d - Watermark Issues"
                    else:
                        return "11.5d - Media Authorization"
                elif first_rule.startswith('11.5e'):
                    return "11.5e - Media Branding"
                elif first_rule.startswith('11.'):
                    return "11.x - Media Rules"
                
                # MLS Usage & Advertising (12.x)
                elif first_rule.startswith('12.1'):
                    if 'DRE' in rule_str or 'OREA' in rule_str:
                        return "12.1 - Regulatory Notifications"
                    else:
                        return "12.1 - False Advertising Standards"
                elif first_rule.startswith('12.5.1'):
                    return "12.5.1 - Other Remarks Misuse"
                elif first_rule.startswith('12.5'):
                    return "12.5 - Public Remarks Standards"
                elif first_rule.startswith('12.7'):
                    return "12.7 - 'Sold' Term Usage"
                elif first_rule.startswith('12.8.1'):
                    return "12.8.1 - Neighborhood Market Reports"
                elif first_rule.startswith('12.8'):
                    return "12.8 - Unauthorized Listing Ads"
                elif first_rule.startswith('12.9'):
                    return "12.9 - Informational Notices"
                elif first_rule.startswith('12.11'):
                    return "12.11 - Unauthorized MLS Use"
                elif first_rule.startswith('12.12'):
                    if 'CLERICAL' in rule_str:
                        return "12.12.1 - Clerical User Access"
                    else:
                        return "12.12 - MLS Data Distribution"
                elif first_rule.startswith('12.15'):
                    if 'CONFIDENTIAL' in rule_str:
                        return "12.15.2 - Confidential Fields"
                    elif 'COMPILATION' in rule_str:
                        return "12.15.4 - Data Compilation"
                    else:
                        return "12.15 - MLS Reproduction"
                elif first_rule.startswith('12.22'):
                    return "12.22 - Email Requirements"
                elif first_rule.startswith('12.'):
                    return "12.x - MLS Usage Rules"
                
                # Lockbox & Security (13.x)
                elif first_rule.startswith('13.2'):
                    return "13.2 - Lockbox Key Sharing"
                elif first_rule.startswith('13.4'):
                    return "13.4 - Lockbox Key Accountability"
                elif first_rule.startswith('13.5'):
                    return "13.5 - Lockbox Placement Permission"
                elif first_rule.startswith('13.6'):
                    return "13.6 - Lockbox Requirements"
                elif first_rule.startswith('13.7'):
                    if 'SHOWING' in rule_str:
                        return "13.7b - Showing Instructions"
                    else:
                        return "13.7 - Unauthorized Property Entry"
                elif first_rule.startswith('13.8'):
                    return "13.8 - Lost/Stolen Key Reporting"
                elif first_rule.startswith('13.9'):
                    return "13.9 - Lockbox Removal"
                elif first_rule.startswith('13.'):
                    return "13.x - Lockbox Rules"
                
                # Compliance & Corrections (14.x)
                elif first_rule.startswith('14.4'):
                    if 'AUTO SOLD' in rule_str:
                        return "14.4 - Auto Sold Corrections"
                    else:
                        return "14.4 - Violation Corrections"
                elif first_rule.startswith('14.5'):
                    return "14.5 - Information Modifications"
                elif first_rule.startswith('14.'):
                    return "14.x - Compliance Rules"
                
                # Internet & Technology (19.x)
                elif first_rule.startswith('19.2'):
                    return "19.2 - IDX Rule Violations"
                elif first_rule.startswith('19.3'):
                    return "19.3 - VOW Rule Violations"
                elif first_rule.startswith('19.'):
                    return "19.x - Internet Rules"
                
                # Special cases
                elif first_rule.startswith('99.'):
                    return "99.x - Test/Development Rules"
                elif 'LISTING' in rule_str and 'MODIFICATION' in rule_str:
                    return "Listing Modifications"
                elif 'NOT APPLICABLE' in rule_str:
                    return "Not Applicable"
                
                # Final fallback
                else:
                    return "Uncategorized Rules"
            
            # Categorize by detailed rules
            df_analysis = filtered_df.copy()
            df_analysis['DetailedRuleCategory'] = df_analysis['RuleNumber'].apply(categorize_detailed_rule)
            
            # Count by rule category
            rule_counts = df_analysis['DetailedRuleCategory'].value_counts().reset_index()
            rule_counts.columns = ['RuleCategory', 'Count']
            
            # Create treemap or grouped bar chart
            if len(rule_counts) <= 8:
                # Use pie chart for smaller number of categories
                colors = px.colors.qualitative.Set2[:len(rule_counts)]
                
                fig = go.Figure(data=[go.Pie(
                    labels=rule_counts['RuleCategory'],
                    values=rule_counts['Count'],
                    hole=0.4,
                    marker=dict(colors=colors, line=dict(color='white', width=2)),
                    hovertemplate="<b>%{label}</b><br>Cases: %{value}<br>Percent: %{percent}<extra></extra>"
                )])
                
                # Add center text
                total_cases = rule_counts['Count'].sum()
                fig.add_annotation(
                    text=f"<b>{total_cases:,}</b><br>Total Cases",
                    x=0.5, y=0.5,
                    font_size=14,
                    showarrow=False
                )
                
                fig.update_layout(
                    title={
                        'text': f"Incidents by Rule Type ({total_cases:,} Cases)",
                        'x': 0.5, 'xanchor': 'center'
                    },
                    height=400
                )
            else:
                # Use horizontal bar chart for many categories
                colors = px.colors.qualitative.Set3[:len(rule_counts)]
                
                fig = go.Figure(data=[go.Bar(
                    y=rule_counts['RuleCategory'],
                    x=rule_counts['Count'],
                    orientation='h',
                    marker=dict(color=colors, line=dict(color='white', width=1)),
                    hovertemplate="<b>%{y}</b><br>Cases: %{x}<extra></extra>",
                    text=rule_counts['Count'],
                    textposition='inside'
                )])
                
                fig.update_layout(
                    title={
                        'text': f"Incidents by Rule Type ({rule_counts['Count'].sum():,} Cases)",
                        'x': 0.5, 'xanchor': 'center'
                    },
                    xaxis_title="Number of Cases",
                    yaxis_title="",
                    height=400,
                    margin={'l': 250, 'r': 50, 't': 80, 'b': 50}
                )
            
        elif view_type == "disposition":
            # Analyze by case disposition/resolution patterns
            disposition_counts = filtered_df['Disposition'].value_counts().reset_index()
            disposition_counts.columns = ['Disposition', 'Count']
            
            # Create stacked bar chart to show disposition distribution
            # Color mapping for different dispositions
            disposition_colors = {
                'Citation': '#dc3545',  # Red - serious
                'Warning': '#fd7e14',   # Orange - moderate
                'Corrected': '#28a745', # Green - resolved
                'No Violation': '#6c757d', # Gray - dismissed
                'Investigation': '#007bff', # Blue - in progress
                'Duplicate': '#6f42c1',    # Purple - administrative
                'Withdrawn': '#20c997',     # Teal - voluntary
            }
            
            # Assign colors
            colors = [disposition_colors.get(disp, '#6c757d') for disp in disposition_counts['Disposition']]
            
            fig = go.Figure(data=[go.Bar(
                x=disposition_counts['Disposition'],
                y=disposition_counts['Count'],
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{x}</b><br>Cases: %{y}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                customdata=disposition_counts['Count'] / disposition_counts['Count'].sum() * 100,
                text=disposition_counts['Count'],
                textposition='outside'
            )])
            
            fig.update_layout(
                title={
                    'text': f"Incidents by Disposition ({disposition_counts['Count'].sum():,} Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Disposition Type",
                yaxis_title="Number of Cases",
                height=400
            )
            
        elif view_type == "frequency":
            # Show most frequently occurring individual violation types
            def get_first_violation(violation_list):
                """Get first violation from list"""
                if isinstance(violation_list, list) and len(violation_list) > 0:
                    return violation_list[0] if violation_list[0] is not None else "Other"
                return "Other"
            
            # Get individual violation frequencies
            df_analysis = filtered_df.copy()
            df_analysis['FirstViolation'] = df_analysis['ViolationName'].apply(get_first_violation)
            
            # Get top 15 most frequent violations
            violation_counts = df_analysis['FirstViolation'].value_counts().head(15).reset_index()
            violation_counts.columns = ['Violation', 'Count']
            
            # Create horizontal bar chart
            colors = px.colors.sequential.Blues_r[:len(violation_counts)]
            
            fig = go.Figure(data=[go.Bar(
                y=violation_counts['Violation'],
                x=violation_counts['Count'],
                orientation='h',
                marker=dict(color=colors, line=dict(color='white', width=1)),
                hovertemplate="<b>%{y}</b><br>Cases: %{x}<br>Percentage: %{customdata:.1f}%<extra></extra>",
                customdata=violation_counts['Count'] / filtered_df.shape[0] * 100,
                text=violation_counts['Count'],
                textposition='inside'
            )])
            
            fig.update_layout(
                title={
                    'text': f"Top 15 Most Frequent Violations ({violation_counts['Count'].sum():,} Cases)",
                    'x': 0.5, 'xanchor': 'center'
                },
                xaxis_title="Number of Cases",
                yaxis_title="",
                height=400,
                margin={'l': 300, 'r': 50, 't': 80, 'b': 50}
            )
        
        # Common layout updates
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            font={'color': '#2c3e50'},
            margin={'t': 80, 'b': 50}
        )
        
        return fig
    
    @monitor_chart_performance("Enlarged Incident Analysis Chart")
    def create_enlarged_incident_analysis_chart(original_figure):
        """Create an enlarged version of the incident analysis chart for modal display"""
        
        if not original_figure or 'data' not in original_figure:
            return {}
        
        # Create enlarged version with updated layout
        enlarged_fig = copy.deepcopy(original_figure)
        
        # Update layout for modal display
        enlarged_fig['layout'].update({
            'height': 600,  # Larger height for modal
            'margin': {'l': 80, 'r': 80, 't': 100, 'b': 70},
            'title': {
                'text': enlarged_fig['layout'].get('title', {}).get('text', 'Incident Analysis'),
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': '#2c3e50'}
            },
            'xaxis': {
                'title': {**enlarged_fig['layout'].get('xaxis', {}).get('title', {}), 'font': {'size': 14}},
                'tickfont': {'size': 12}
            },
            'yaxis': {
                'title': {**enlarged_fig['layout'].get('yaxis', {}).get('title', {}), 'font': {'size': 14}},
                'tickfont': {'size': 12}
            }
        })
        
        # Adjust margins for different chart types
        if 'margin' in enlarged_fig['layout']:
            current_margin = enlarged_fig['layout']['margin']
            if current_margin.get('l', 0) > 200:  # Horizontal bar charts need more left margin
                enlarged_fig['layout']['margin']['l'] = max(current_margin['l'] + 50, 350)
        
        return enlarged_fig
    
    @monitor_performance("Incident Analysis Insights Generation")
    def generate_incident_analysis_insights(filtered_df, view_type):
        """Generate insights for incident analysis"""
        
        if filtered_df.empty:
            return html.Div([
                html.Div([
                    html.Span("📊 ", style={'fontSize': '16px'}),
                    html.Span("**No Data**: No incident data available for analysis", style={'fontSize': '13px'})
                ], className="mb-2")
            ], className="insights-container")
        
        insights = []
        total_cases = len(filtered_df)
        
        try:
            if view_type == "category":
                # Category-specific insights
                def categorize_rule_violation(rule_list):
                    if not isinstance(rule_list, list) or len(rule_list) == 0:
                        return "Other Violations"
                    first_rule = str(rule_list[0]) if rule_list[0] is not None else ""
                    if first_rule.startswith('7.'):
                        return "Listing Violations"
                    elif first_rule.startswith('12.'):
                        return "MLS Usage Violations"
                    elif first_rule.startswith('11.'):
                        return "Media Violations"
                    else:
                        return "Other Violations"
                
                filtered_df['ViolationCategory'] = filtered_df['RuleNumber'].apply(categorize_rule_violation)
                category_counts = filtered_df['ViolationCategory'].value_counts()
                
                # Most problematic category
                top_category = category_counts.index[0]
                top_count = category_counts.iloc[0]
                
                insights.append(
                    html.Div([
                        html.Span("🎯 ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Problematic Category**: {top_category} accounts for {top_count:,} cases ({top_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Category distribution
                unique_categories = len(category_counts)
                insights.append(
                    html.Div([
                        html.Span("📊 ", style={'fontSize': '16px'}),
                        html.Span(f"**Category Distribution**: {unique_categories} violation categories identified across all incidents", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Second most common category
                if len(category_counts) > 1:
                    second_category = category_counts.index[1]
                    second_count = category_counts.iloc[1]
                    insights.append(
                        html.Div([
                            html.Span("📈 ", style={'fontSize': '16px'}),
                            html.Span(f"**Secondary Issue**: {second_category} represents {second_count:,} cases ({second_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
            elif view_type == "rule":
                # Rule-specific insights
                def categorize_detailed_rule(rule_list):
                    if not isinstance(rule_list, list) or len(rule_list) == 0:
                        return "Other"
                    first_rule = str(rule_list[0]) if rule_list[0] is not None else ""
                    if first_rule.startswith('7.'):
                        return "7.x - Listing Rules"
                    elif first_rule.startswith('12.'):
                        return "12.x - MLS Usage Rules"
                    elif first_rule.startswith('11.'):
                        return "11.x - Media Rules"
                    else:
                        return "Other Rules"
                
                filtered_df['DetailedRuleCategory'] = filtered_df['RuleNumber'].apply(categorize_detailed_rule)
                rule_counts = filtered_df['DetailedRuleCategory'].value_counts()
                
                # Most violated rule category
                top_rule_category = rule_counts.index[0]
                top_rule_count = rule_counts.iloc[0]
                
                insights.append(
                    html.Div([
                        html.Span("⚖️ ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Violated Rules**: {top_rule_category} with {top_rule_count:,} incidents ({top_rule_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Rule coverage
                unique_rule_categories = len(rule_counts)
                insights.append(
                    html.Div([
                        html.Span("📋 ", style={'fontSize': '16px'}),
                        html.Span(f"**Rule Coverage**: {unique_rule_categories} different rule categories involved in compliance incidents", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Specific rule insights
                if "7.x - Listing Rules" in rule_counts.index:
                    listing_pct = rule_counts["7.x - Listing Rules"] / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("🏠 ", style={'fontSize': '16px'}),
                            html.Span(f"**Listing Rule Impact**: {listing_pct:.1f}% of all incidents involve listing rule violations", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                elif "12.x - MLS Usage Rules" in rule_counts.index:
                    mls_pct = rule_counts["12.x - MLS Usage Rules"] / total_cases * 100
                    insights.append(
                        html.Div([
                            html.Span("🗂️ ", style={'fontSize': '16px'}),
                            html.Span(f"**MLS Rule Impact**: {mls_pct:.1f}% of all incidents involve MLS usage violations", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
            elif view_type == "disposition":
                # Disposition-specific insights
                disposition_counts = filtered_df['Disposition'].value_counts()
                
                # Most common disposition
                top_disposition = disposition_counts.index[0]
                top_disp_count = disposition_counts.iloc[0]
                
                insights.append(
                    html.Div([
                        html.Span("📊 ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Common Resolution**: {top_disposition} accounts for {top_disp_count:,} cases ({top_disp_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Resolution patterns
                citation_count = disposition_counts.get('Citation', 0)
                warning_count = disposition_counts.get('Warning', 0)
                corrected_count = disposition_counts.get('Corrected', 0)
                
                if citation_count > 0:
                    insights.append(
                        html.Div([
                            html.Span("🚨 ", style={'fontSize': '16px'}),
                            html.Span(f"**Serious Violations**: {citation_count:,} cases resulted in citations ({citation_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
                if corrected_count > 0:
                    insights.append(
                        html.Div([
                            html.Span("✅ ", style={'fontSize': '16px'}),
                            html.Span(f"**Voluntary Corrections**: {corrected_count:,} cases were corrected proactively ({corrected_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
            elif view_type == "frequency":
                # Frequency-specific insights
                def get_first_violation(violation_list):
                    if isinstance(violation_list, list) and len(violation_list) > 0:
                        return violation_list[0] if violation_list[0] is not None else "Other"
                    return "Other"
                
                filtered_df['FirstViolation'] = filtered_df['ViolationName'].apply(get_first_violation)
                violation_counts = filtered_df['FirstViolation'].value_counts()
                
                # Most frequent violation
                top_violation = violation_counts.index[0]
                top_violation_count = violation_counts.iloc[0]
                
                insights.append(
                    html.Div([
                        html.Span("🔥 ", style={'fontSize': '16px'}),
                        html.Span(f"**Most Frequent Violation**: {top_violation} with {top_violation_count:,} incidents ({top_violation_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Frequency concentration
                top_5_count = violation_counts.head(5).sum()
                insights.append(
                    html.Div([
                        html.Span("📈 ", style={'fontSize': '16px'}),
                        html.Span(f"**Concentration Analysis**: Top 5 violation types account for {top_5_count:,} incidents ({top_5_count/total_cases*100:.1f}%)", style={'fontSize': '13px'})
                    ], className="mb-2")
                )
                
                # Recurring issues identification
                unique_violations = len(violation_counts)
                if unique_violations <= 10:
                    insights.append(
                        html.Div([
                            html.Span("🔍 ", style={'fontSize': '16px'}),
                            html.Span(f"**Focused Issues**: Only {unique_violations} distinct violation types - suggests concentrated compliance problems", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                else:
                    insights.append(
                        html.Div([
                            html.Span("🌐 ", style={'fontSize': '16px'}),
                            html.Span(f"**Diverse Issues**: {unique_violations} different violation types identified across incidents", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                
        except Exception as e:
            print(f"Error generating incident analysis insights: {e}")
            insights = [
                html.Div([
                    html.Span("🔄 ", style={'fontSize': '16px'}),
                    html.Span("**Processing**: Incident analysis is being processed...", style={'fontSize': '13px'})
                ], className="mb-2"),
                html.Div([
                    html.Span("📊 ", style={'fontSize': '16px'}),
                    html.Span(f"**Dataset**: Analyzing {total_cases:,} compliance incidents", style={'fontSize': '13px'})
                ], className="mb-2"),
                html.Div([
                    html.Span("📋 ", style={'fontSize': '16px'}),
                    html.Span(f"**View**: Showing incident analysis by {view_type}", style={'fontSize': '13px'})
                ], className="mb-2")
            ]
        
        # Ensure we always have at least 3 insights
        if len(insights) < 3:
            while len(insights) < 3:
                if len(insights) == 1:
                    insights.append(
                        html.Div([
                            html.Span("📊 ", style={'fontSize': '16px'}),
                            html.Span(f"**Analysis Scope**: Examining {total_cases:,} incidents across multiple violation categories", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
                elif len(insights) == 2:
                    insights.append(
                        html.Div([
                            html.Span("🎯 ", style={'fontSize': '16px'}),
                            html.Span(f"**View Focus**: Current analysis shows incidents grouped by {view_type} patterns", style={'fontSize': '13px'})
                        ], className="mb-2")
                    )
        
        return html.Div(insights, className="insights-container")
    
    # Main callback for updating chart and insights
    @callback(
        [Output("compliance-incident-analysis-chart", "figure"),
         Output("compliance-incident-analysis-insights", "children")],
        [Input("compliance-filtered-query-store", "data"),
         Input("compliance-incident-view-dropdown", "value")],
        prevent_initial_call=False
    )
    @monitor_performance("Incident Analysis Chart Update")
    def update_incident_analysis_chart(filter_selections, view_type):
        """Update incident analysis chart and insights"""
        
        try:
            # Get base compliance data
            base_df = get_compliance_base_data()
            
            if base_df.empty:
                return {}, html.Div("No compliance data available")
            
            # Apply filters if any
            if filter_selections:
                filtered_df = apply_compliance_filters(base_df, filter_selections)
            else:
                filtered_df = base_df
            
            # Generate chart and insights
            chart_figure = create_incident_analysis_chart(filtered_df, view_type or "category")
            insights_content = generate_incident_analysis_insights(filtered_df, view_type or "category")
            
            return chart_figure, insights_content
            
        except Exception as e:
            print(f"Error updating incident analysis: {e}")
            return {}, html.Div(f"Error: {str(e)}", className="text-danger")
    
    # Chart modal callback for enlarged view
    @callback(
        [
            Output("compliance-chart-modal", "is_open", allow_duplicate=True),
            Output("compliance-modal-chart-content", "children", allow_duplicate=True)
        ],
        [
            Input("compliance-incident-analysis-chart-wrapper", "n_clicks")
        ],
        [
            State("compliance-incident-analysis-chart", "figure"),
            State("compliance-chart-modal", "is_open")
        ],
        prevent_initial_call=True
    )
    def toggle_incident_analysis_chart_modal(wrapper_clicks, chart_figure, is_open_state):
        """Toggle enlarged incident analysis chart modal on chart wrapper click"""
        
        if wrapper_clicks and not is_open_state and chart_figure:
            enlarged_chart = create_enlarged_incident_analysis_chart(chart_figure)
            return True, dcc.Graph(
                figure=enlarged_chart,
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 
                                           'drawcircle', 'drawrect', 'eraseshape'],
                    'toImageButtonOptions': {
                        'format': 'png',
                        'filename': 'incident_analysis_chart',
                        'height': 600,
                        'width': 1200,
                        'scale': 2
                    }
                }
            )
        
        return no_update, no_update

    # print("✅ Compliance incident analysis callbacks registered")