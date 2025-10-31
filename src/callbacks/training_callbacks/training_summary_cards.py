from dash import clientside_callback, Input, Output

def register_training_summary_cards_callbacks(app):
    """
    Register client-side callback for training summary cards using TrainingSummaryUtils class
    """
    # print("Registering Client-side Training Summary Cards callback...")
    
    # Stage 1: Show spinners immediately
    clientside_callback(
        """
        function(filtered_data, query_selections) {
            return window.TrainingSummaryUtils.createSummarySpinnerStates(true);
        }
        """,
        [
            Output("total-classes-spinner", "spinner_style"),
            Output("total-attendances-spinner", "spinner_style"),
            Output("total-requests-spinner", "spinner_style"),
            Output("active-members-spinner", "spinner_style")
        ],
        [
            Input("training-filtered-data-store", "data"),
            Input("training-filtered-query-store", "data")
        ],
        prevent_initial_call=True
    )
    
    # Stage 2: Calculate and update values + hide spinners (FIXED PROPERTY EXTRACTION)
    clientside_callback(
        """
        function(filtered_data, query_selections) {
            return new Promise((resolve) => {
                setTimeout(() => {
                    try {                        
                        const result = window.TrainingSummaryUtils.updateSummaryCards(
                            filtered_data, 
                            query_selections
                        );                        
                        const values = result.values || ["0", "0", "0", "0"];                        
                        const hideSpinners = window.TrainingSummaryUtils.createSummarySpinnerStates(false);
                        resolve([
                            ...values,         
                            ...hideSpinners    
                        ]);                        
                    } catch (error) {
                        const hideSpinners = window.TrainingSummaryUtils.createSummarySpinnerStates(false);
                        resolve([
                            "0", "0", "0", "0",  
                            ...hideSpinners       
                        ]);
                    }
                }, 100);
            });
        }
        """,
        [
            # Card values
            Output("total-classes-card", "children"),
            Output("total-attendances-card", "children"),
            Output("total-requests-card", "children"),
            Output("active-members-card", "children"),
            # Spinner states
            Output("total-classes-spinner", "spinner_style", allow_duplicate=True),
            Output("total-attendances-spinner", "spinner_style", allow_duplicate=True),
            Output("total-requests-spinner", "spinner_style", allow_duplicate=True),
            Output("active-members-spinner", "spinner_style", allow_duplicate=True)
        ],
        [
            Input("training-filtered-data-store", "data"),
            Input("training-filtered-query-store", "data")
        ],
        prevent_initial_call=True
    )
    # print("✅ Client-side Training Summary Cards callback registered successfully")