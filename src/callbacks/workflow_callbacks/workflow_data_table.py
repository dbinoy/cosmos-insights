from dash import callback, ctx, dcc, html, Input, Output, State, no_update, dash_table
import pandas as pd
from datetime import datetime
from src.utils.db import run_queries
from src.utils.performance import monitor_performance, monitor_query_performance

def register_workflow_data_table_callbacks(app):
    """
    Register workflow data table callbacks with export functionality.
    Matches the component IDs from the layout file.
    """

    @monitor_query_performance("Workflow Data Table Base Data")
    def get_workflow_data_table_base_data():
        queries = {
            "Fact_WorkFlowItems": "SELECT * FROM [consumable].[Fact_WorkFlowItems]",
            "Fact_AssignmentDurations": "SELECT * FROM [consumable].[Fact_AssignmentDurations]",
            "Fact_EscalationDurations": "SELECT * FROM [consumable].[Fact_EscalationDurations]",
        }
        return run_queries(queries, 'workflow', len(queries))

    @monitor_performance("Workflow Data Table Filter Application")
    def apply_workflow_data_table_filters(work_items, query_selections):
        """Filter Fact_WorkFlowItems DataFrame based on all supported fields."""
        if work_items.empty:
            return work_items
        print(f"Applying workflow data table filters: {query_selections}")
        # Parse filter values
        selected_aor = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('AOR', '').split(', ') if item.strip("'")]
        selected_case_types = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('CaseTypes', '').split(', ') if item.strip("'")]
        selected_status = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('Status', '').split(', ') if item.strip("'")]
        selected_priority = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('Priority', '').split(', ') if item.strip("'")]
        selected_origins = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('Origins', '').split(', ') if item.strip("'")]
        selected_reasons = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('Reasons', '').split(', ') if item.strip("'")]
        selected_products = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('Products', '').split(', ') if item.strip("'")]
        selected_features = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('Features', '').split(', ') if item.strip("'")]
        selected_modules = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('Modules', '').split(', ') if item.strip("'")]
        selected_issues = [item.strip("'") if item != "'-'" else "" for item in query_selections.get('Issues', '').split(', ') if item.strip("'")]
        start_date = query_selections.get('Day_From')
        end_date = query_selections.get('Day_To')
        # print(f"Selected Filters - AORs: [{selected_aor}], CaseTypes: [{selected_case_types}], Status: [{selected_status}], Priority: [{selected_priority}], Origins: [{selected_origins}], Reasons: [{selected_reasons}], Products: [{selected_products}], Features: [{selected_features}], Modules: [{selected_modules}], Issues: [{selected_issues}], Date Range: [{start_date}] to [{end_date}]")

        # Parse dates
        if 'CreatedOn' in work_items.columns:
            work_items['CreatedOn'] = pd.to_datetime(work_items['CreatedOn'], errors='coerce')
            work_items = work_items.dropna(subset=['CreatedOn']).copy()
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    work_items = work_items.loc[
                        (work_items['CreatedOn'] >= start_dt) & 
                        (work_items['CreatedOn'] <= end_dt)
                    ].copy()
                except Exception as e:
                    print(f"❌ Error applying date filter: {e}")

        # Apply other filters
        if selected_aor and "All" not in selected_aor and 'AorShortName' in work_items.columns:
            work_items = work_items[work_items['AorShortName'].isin(selected_aor)].copy()
        if selected_case_types and "All" not in selected_case_types and 'WorkItemDefinitionShortCode' in work_items.columns:
            work_items = work_items[work_items['WorkItemDefinitionShortCode'].isin(selected_case_types)].copy()
        if selected_status and "All" not in selected_status and 'WorkItemStatus' in work_items.columns:
            work_items = work_items[work_items['WorkItemStatus'].isin(selected_status)].copy()
        if selected_priority and "All" not in selected_priority and 'Priority' in work_items.columns:
            work_items = work_items[work_items['Priority'].isin(selected_priority)].copy()
        if selected_origins and "All" not in selected_origins and 'CaseOrigin' in work_items.columns:
            work_items = work_items[work_items['CaseOrigin'].isin(selected_origins)].copy()
        if selected_reasons and "All" not in selected_reasons and 'CaseReason' in work_items.columns:
            work_items = work_items[work_items['CaseReason'].isin(selected_reasons)].copy()
        if selected_products and "All" not in selected_products and 'Product' in work_items.columns:
            work_items = work_items[work_items['Product'].isin(selected_products)].copy()
        if selected_features and "All" not in selected_features and 'Feature' in work_items.columns:
            work_items = work_items[work_items['Feature'].isin(selected_features)].copy()
        if selected_modules and "All" not in selected_modules and 'Module' in work_items.columns:
            work_items = work_items[work_items['Module'].isin(selected_modules)].copy()
        if selected_issues and "All" not in selected_issues and 'Issue' in work_items.columns:
            work_items = work_items[work_items['Issue'].isin(selected_issues)].copy()

        return work_items
    
    @monitor_performance("Workflow Data Table Report Preparation")
    def prepare_workflow_data_table_report(base_data, query_selections, report_type):
        """
        Compose the required report using pandas, joining tables as needed.
        """
        df_items = pd.DataFrame(base_data.get("Fact_WorkFlowItems", []))
        df_items = apply_workflow_data_table_filters(df_items, query_selections)
        df_assign = pd.DataFrame(base_data.get("Fact_AssignmentDurations", []))
        df_escal = pd.DataFrame(base_data.get("Fact_EscalationDurations", []))

        if report_type == "ticket_summary":
            # Select and rename columns
            mapping = {
                'WorkItemId': 'Ticket ID',
                'Title': 'Title',
                'CreatedOn': 'Created On',
                'ClosedOn': 'Closed On',
                'WorkItemStatus': 'Status',
                'WorkItemDefinitionShortCode': 'Type',
                'AorShortName': 'AOR',
                'CaseOrigin': 'Origin',
                'CaseReason': 'Reason',
                'Feature': 'Feature',
                'Issue': 'Issue',
                'Module': 'Module',
                'Priority': 'Priority',
                'Product': 'Product',
                'AssignedTo': 'Assigned To',
                'IsEscalated': 'Escalated',
                'EscalationOwner': 'Escalation Owner'
            }
            cols = [c for c in mapping if c in df_items.columns]
            df = df_items[cols].rename(columns=mapping)
            return df

        elif report_type == "resolution_details":
            # Filter closed tickets
            df = df_items[df_items['ClosedOn'].notnull()].copy()
            mapping = {
                'WorkItemId': 'Ticket ID',
                'Title': 'Title',
                'ResolutionSummary': 'Resolution',
                'ClosedOn': 'Closed On',
                'AssignedTo': 'Assigned To',
                'WorkItemStatus': 'Status',
                'Priority': 'Priority',
                'Product': 'Product'
            }
            cols = [c for c in mapping if c in df.columns]
            df = df[cols].rename(columns=mapping)
            return df

        elif report_type == "user_performance":
            # Merge assignment durations with ticket info
            if not df_assign.empty and not df_items.empty:
                df = pd.merge(df_assign, df_items, on="WorkItemId", how="left", suffixes=("_assign", "_item"))
                mapping = {
                    'WorkItemId': 'Ticket ID',
                    'AssignedFrom': 'Assigned From',
                    'AssignedTo': 'Assigned To',
                    'FromUserId': 'From User',
                    'ToUserId': 'To User',
                    'DurationHours': 'Assignment Duration (hrs)',
                    'Title': 'Title',
                    'CreatedOn': 'Created On',
                    'ClosedOn': 'Closed On',
                    'WorkItemStatus': 'Status',
                    'Priority': 'Priority',
                    'Product': 'Product'
                }
                cols = [c for c in mapping if c in df.columns]
                df = df[cols].rename(columns=mapping)
                return df
            else:
                return pd.DataFrame()

        elif report_type == "escalation_history":
            # Merge escalation durations with ticket info
            if not df_escal.empty and not df_items.empty:
                df = pd.merge(df_escal, df_items, on="WorkItemId", how="left", suffixes=("_escal", "_item"))
                mapping = {
                    'WorkItemId': 'Ticket ID',
                    'AssignedFrom': 'Escalation From',
                    'AssignedTo': 'Escalation To',
                    'FromUserId': 'Escalated By',
                    'ToUserId': 'Escalation Owner',
                    'DurationHours': 'Escalation Duration (hrs)',
                    'Title': 'Title',
                    'CreatedOn': 'Created On',
                    'ClosedOn': 'Closed On',
                    'WorkItemStatus': 'Status',
                    'Priority': 'Priority',
                    'Product': 'Product'
                }
                cols = [c for c in mapping if c in df.columns]
                df = df[cols].rename(columns=mapping)
                return df
            else:
                return pd.DataFrame()

        elif report_type == "product_impact":
            mapping = {
                'Product': 'Product',
                'WorkItemId': 'Ticket ID',
                'Title': 'Title',
                'CreatedOn': 'Created On',
                'ClosedOn': 'Closed On',
                'WorkItemStatus': 'Status',
                'Priority': 'Priority',
                'Module': 'Module',
                'Feature': 'Feature',
                'Issue': 'Issue'
            }
            cols = [c for c in mapping if c in df_items.columns]
            df = df_items[cols].rename(columns=mapping)
            return df

        else:
            return pd.DataFrame()
        
    @callback(
        Output("workflow-data-table-container", "children"),
        [
            Input("workflow-filtered-query-store", "data"),
            Input("workflow-data-table-report-type-dropdown", "value"),
            Input("workflow-table-page-size-dropdown", "value")
        ],
        prevent_initial_call=False
    )
    @monitor_performance("Workflow Data Table Update")
    def update_workflow_data_table(query_selections, report_type, page_size):
        try:
            base_data = get_workflow_data_table_base_data()
            report_df = prepare_workflow_data_table_report(base_data, query_selections, report_type)

            if report_df.empty:
                return html.Div([
                    html.P("No data available for the selected filters and report type.",
                        className="text-muted text-center p-4")
                ])

            # Format datetime columns
            for col in report_df.columns:
                if report_df[col].dtype == 'datetime64[ns]':
                    report_df[col] = report_df[col].dt.strftime('%Y-%m-%d %H:%M')

            columns = [{"name": col, "id": col, "deletable": False, "selectable": False} for col in report_df.columns]

            style_data_conditional = [
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
            ]

            data_table = dash_table.DataTable(
                id="workflow-data-table",
                columns=columns,
                data=report_df.to_dict('records'),
                page_size=page_size,
                sort_action="native",
                sort_mode="multi",
                filter_action="native",
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
                style_cell={'textAlign': 'left', 'padding': '10px', 'fontFamily': 'Arial, sans-serif', 'fontSize': '12px', 'border': '1px solid #dee2e6'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'color': '#495057', 'border': '1px solid #dee2e6'},
                style_data_conditional=style_data_conditional,
                css=[{'selector': '.dash-table-tooltip', 'rule': 'background-color: grey; font-family: monospace; color: white'}]
            )

            summary_info = html.Div([
                html.P([
                    html.Strong(f"Showing {len(report_df):,} records"),
                    f" • Report: {report_type.replace('_', ' ').title()}",
                    f" • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ], className="text-muted small mb-3")
            ])

            return html.Div([summary_info, data_table])

        except Exception as e:
            print(f"❌ Error updating workflow data table: {e}")
            return html.Div([
                html.P(f"Error loading data table: {str(e)}",
                    className="text-danger text-center p-4")
            ])               

    @callback(
        Output("workflow-download-csv", "data"),
        Input("workflow-export-csv-btn", "n_clicks"),
        [
            State("workflow-filtered-query-store", "data"),
            State("workflow-data-table-report-type-dropdown", "value")
        ],
        prevent_initial_call=True
    )
    def export_workflow_csv(n_clicks, query_selections, report_type):
        if not n_clicks:
            return no_update
        try:
            base_data = get_workflow_data_table_base_data()
            report_df = prepare_workflow_data_table_report(base_data, query_selections, report_type)
            if report_df.empty:
                return no_update
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"workflow_{report_type}_{timestamp}.csv"
            return dcc.send_data_frame(report_df.to_csv, filename, index=False)
        except Exception as e:
            print(f"❌ Error exporting CSV: {e}")
            return no_update

    @callback(
        Output("workflow-download-excel", "data"),
        Input("workflow-export-excel-btn", "n_clicks"),
        [
            State("workflow-filtered-query-store", "data"),
            State("workflow-data-table-report-type-dropdown", "value")
        ],
        prevent_initial_call=True
    )
    def export_workflow_excel(n_clicks, query_selections, report_type):
        if not n_clicks:
            return no_update
        try:
            base_data = get_workflow_data_table_base_data()
            report_df = prepare_workflow_data_table_report(base_data, query_selections, report_type)
            if report_df.empty:
                return no_update
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                sheet_name = report_type.replace('_', ' ').title()[:31]
                report_df.to_excel(writer, sheet_name=sheet_name, index=False)
            buffer.seek(0)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"workflow_{report_type}_{timestamp}.xlsx"
            return dcc.send_bytes(buffer.getvalue(), filename=filename)
        except Exception as e:
            print(f"❌ Error exporting Excel: {e}")
            return no_update

    @callback(
        Output("workflow-download-pdf", "data"),
        Input("workflow-export-pdf-btn", "n_clicks"),
        [
            State("workflow-filtered-query-store", "data"),
            State("workflow-data-table-report-type-dropdown", "value")
        ],
        prevent_initial_call=True
    )
    def export_workflow_pdf(n_clicks, query_selections, report_type):
        if not n_clicks:
            return no_update
        try:
            base_data = get_workflow_data_table_base_data()
            report_df = prepare_workflow_data_table_report(base_data, query_selections, report_type)
            if report_df.empty:
                return no_update
            import io
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.lib import colors

            buffer = io.BytesIO()
            page_size = landscape(A4) if len(report_df.columns) > 6 else A4
            page_width = page_size[0]

            doc = SimpleDocTemplate(buffer, pagesize=page_size, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=1*inch, bottomMargin=0.5*inch)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.black, alignment=TA_CENTER, spaceAfter=0.3*inch)
            subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Normal'], fontSize=10, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=0.2*inch)
            cell_text_style = ParagraphStyle('CellText', parent=styles['Normal'], fontSize=8, textColor=colors.black, alignment=TA_LEFT, leading=10, leftIndent=2, rightIndent=2, spaceAfter=2, wordWrap='LTR')
            cell_numeric_style = ParagraphStyle('CellNumeric', parent=styles['Normal'], fontSize=8, textColor=colors.black, alignment=TA_RIGHT, leading=10, leftIndent=2, rightIndent=2, spaceAfter=2)
            cell_center_style = ParagraphStyle('CellCenter', parent=styles['Normal'], fontSize=8, textColor=colors.black, alignment=TA_CENTER, leading=10, leftIndent=2, rightIndent=2, spaceAfter=2)
            header_style = ParagraphStyle('HeaderText', parent=styles['Normal'], fontSize=9, textColor=colors.whitesmoke, alignment=TA_CENTER, leading=11, fontName='Helvetica-Bold', leftIndent=2, rightIndent=2)

            elements = []
            report_title = report_type.replace('_', ' ').title()
            title = Paragraph(f"Workflow Activity Report: {report_title}", title_style)
            elements.append(title)
            current_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
            subtitle = Paragraph(f"Generated on {current_time} • {len(report_df):,} records", subtitle_style)
            elements.append(subtitle)
            elements.append(Spacer(1, 0.2*inch))

            headers = list(report_df.columns)
            num_cols = len(headers)
            available_width = page_width - 1*inch

            def calculate_column_widths(df, headers, available_width):
                min_width = 1.0*inch
                max_width = 3.0*inch
                column_weights = {}
                for col in headers:
                    sample_data = df[col].head(20).astype(str)
                    avg_length = sample_data.str.len().mean()
                    max_length = sample_data.str.len().max()
                    header_length = len(col)
                    weight = min(max_width, max(min_width, avg_length * 0.05*inch))
                    column_weights[col] = weight
                total_weight = sum(column_weights.values())
                if total_weight > available_width:
                    scale_factor = available_width / total_weight
                    column_weights = {col: weight * scale_factor for col, weight in column_weights.items()}
                elif total_weight < available_width:
                    extra_space = available_width - total_weight
                    for col in column_weights:
                        column_weights[col] += extra_space / num_cols
                return [column_weights[col] for col in headers]

            col_widths = calculate_column_widths(report_df, headers, available_width)
            table_data = []
            header_row = [Paragraph(str(header), header_style) for header in headers]
            table_data.append(header_row)
            max_rows = 100
            for i, row in report_df.head(max_rows).iterrows():
                row_data = []
                for col_idx, val in enumerate(row):
                    col_name = headers[col_idx]
                    if pd.isna(val):
                        cell_content = ""
                        cell_paragraph = Paragraph(cell_content, cell_text_style)
                    elif isinstance(val, (int, float)):
                        cell_content = str(int(val)) if isinstance(val, float) and val == int(val) else str(val)
                        cell_paragraph = Paragraph(cell_content, cell_numeric_style)
                    else:
                        text = str(val).strip()
                        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
                        cell_paragraph = Paragraph(text, cell_text_style)
                    row_data.append(cell_paragraph)
                table_data.append(row_data)

            table = Table(table_data, colWidths=col_widths, repeatRows=1, splitByRow=True)
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
                ('LINEBEFORE', (0, 0), (0, -1), 2, colors.black),
                ('LINEAFTER', (-1, 0), (-1, -1), 2, colors.black),
                ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black),
            ])
            table.setStyle(table_style)
            elements.append(table)
            if len(report_df) > max_rows:
                footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
                elements.append(Spacer(1, 0.2*inch))
                footer_text = f"Note: Showing first {max_rows} records of {len(report_df):,} total records. Use Excel export for complete data."
                footer = Paragraph(footer_text, footer_style)
                elements.append(footer)
            wrap_note_style = ParagraphStyle('WrapNote', parent=styles['Normal'], fontSize=7, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=0.1*inch)
            elements.append(Spacer(1, 0.1*inch))
            wrap_note = Paragraph("All text content is preserved with automatic wrapping for readability.", wrap_note_style)
            elements.append(wrap_note)
            doc.build(elements)
            buffer.seek(0)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"workflow_{report_type}_{timestamp}.pdf"
            return dcc.send_bytes(buffer.getvalue(), filename=filename)
        except Exception as e:
            print(f"❌ Error exporting PDF: {e}")
            return no_update
        