# Get precommix from separate location, synced with last template update
import (builtins.fetchGit {
  url = "https://gitlab.com/moduon/precommix.git";
  rev = "caf445aa3476fd73f344288d135ffa5234e06982";
})
