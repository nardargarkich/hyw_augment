class ApertiumAnalyzer:
    def __init__(self, apertium_dir=None):
        # Try to find it
        self.available = self._detect(apertium_dir)
    
    def _detect(self, apertium_dir):
        # Check if apertium binary exists
        # Check if the hyw transducer is compiled
        # Return True/False
        ...
    
    def analyze(self, form):
        if not self.available:
            return []
        ...