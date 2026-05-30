
import re

class AskPattern:
    """A string pattern for questions for usage in `--ask` arguments."""
    
    def __init__(self, pattern: str) -> None:
        self.orginal = pattern
        escaped = re.escape(pattern)
        self.pattern = re.compile(
            escaped.replace(r"\*", ".*")
        )
        self.was_matched = False
    
    def matches(self, input: str) -> bool:
        """Check if the pattern matches a string."""
        ret = bool(self.pattern.fullmatch(input))
        if ret:
            self.was_matched = True
        return ret