"""Wrapper classes for data objects"""

class DataObject():
    def __init__(self):
        pass

    @property
    def columns(self):
        raise NotImplementedError("This is a base class")

    @property
    def index(self):
        raise NotImplementedError("This is a base class")
    
    def get_value(self):
        raise NotImplementedError("This is a base class")

    def set_value(self, val):
        raise NotImplementedError("This is a base class")

    def get_column(self):
        raise NotImplementedError("This is a base class")
    
    def set_column(self, column):
        raise NotImplementedError("This is a base class")

    def get_subindex(self):
        raise NotImplementedError("This is a base class")

    def set_subindex(self, val):
        raise NotImplementedError("This is a base class")

    def get_subindices(self):
        raise NotImplementedError("This is a base class")
    
class DataFrame(DataObject):
    def __init__(self, data, selector=None):
        self._data = data
        self._column = data.columns[0]
        self._index = data.index[0]
        self._selector = selector

    @property
    def columns(self):
        return self._data.columns

    def index(self):
        return self._data.index

    def get_index(self):
        return self._index

    def set_index(self, index):
        if index in self.index:
            self._index = index
        else:
            raise KeyError("Invalid index set.")

    def get_column(self):
        return self._column
    
    def set_column(self, column):
        if column in self.columns:
            self._column = column
        else:
            raise KeyError("Invalid column set.")        

    def get_value(self):
        return self._data.at[self._index, self._column]
