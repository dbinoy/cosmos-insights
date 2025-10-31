from dash import clientside_callback, Input, Output

def register_training_summary_cards_callbacks(app):
    """
    Register client-side callback for training summary cards using TrainingSummaryUtils class
    """
    # print("Registering Client-side Training Summary Cards callback...")
    
    clientside_callback(
        """
        function(filtered_data, query_selections) {
            return window.TrainingSummaryUtils.updateSummaryCards(
                filtered_data, 
                query_selections
            );
        }
        """,
        [Output("total-classes-card", "children"),
         Output("total-attendances-card", "children"),
         Output("total-requests-card", "children"),
         Output("active-members-card", "children")],
        [Input("training-filtered-data-store", "data"),
         Input("training-filtered-query-store", "data")],
        prevent_initial_call=True
    )
    
    # print("✅ Client-side Training Summary Cards callback registered successfully")