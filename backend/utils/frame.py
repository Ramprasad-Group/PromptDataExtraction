"""
Create dynamic dataframes.
"""

import pandas as pd

class Frame:
    """ Iteratively build a dictionary for a dataframe.
    """
    def __init__(self, columns = None) -> None:
        self._tabl = {}
        self._cols = columns
        self._df = None

    def _setup_columns(self):
        """ Initialize the dictionary items. """
        for key in self._cols:
            if not key in self._tabl:
                self._tabl[key] = []

    def contains(self, column, value):
        """ Check if a value already exists in a column. """
        if column in self._tabl.keys():
            return value in self._tabl[column]
        else: return False
    
    def pad_columns(self):
        """ Make sure all columns are of same size.
            Add NA to pad the shorter columns.
        """
        max_len = 0
        for key in self._cols:
            col_len = len(self._tabl[key])
            if col_len > max_len:
                max_len = col_len

        for key in self._cols:
            col_len = len(self._tabl[key])
            while col_len < max_len:
                self._tabl[key].append(None)
                col_len = len(self._tabl[key])

    def add(self, **kwargs):
        """ Add row to dataframe. Use named arguments for the column values. """
        self._df = None
        if self._cols is None:
            self._cols = kwargs.keys()

        self._setup_columns()

        for key in kwargs:
            value = kwargs[key]
            if key in self._cols:
                self._tabl[key].append(value)

    @property
    def df(self):
        if self._df is None:
            self._df = pd.DataFrame(self._tabl)
        return self._df

