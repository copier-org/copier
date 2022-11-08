# Get precommix from separate location, synced with last template update
import (builtins.fetchGit {
  url = "https://gitlab.com/moduon/precommix.git";
  ref = "main";
  rev = "43d1213cc0ecda4de610f809f86821207fe5ee63";
})
