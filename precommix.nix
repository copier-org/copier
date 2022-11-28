# Get precommix from separate location, synced with last template update
import (builtins.fetchGit {
  url = "https://gitlab.com/moduon/precommix.git";
  ref = "main";
  rev = "d1054f605511a2fc78783671783fa8c33f7b2416";
})
