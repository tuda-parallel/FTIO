class FreqData:
    """contains the data from the frequency analysis including the 
    1. bandwidth over time spaced with constant steps (1/freq)
    2. settings
    3. original data before sampling
    """
    def __init__(self, df1, df2, df3):
        self.data_df      = df1
        self.settings_df  = df2
        self.original_df  = df3
