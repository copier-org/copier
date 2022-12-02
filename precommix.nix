# Get precommix from separate location, synced with last template update
import (builtins.fetchGit {
  url = "https://gitlab.com/moduon/precommix.git";
  ref = "main";
  rev = "432dbb601d62ce741672e5f8cb1c4d67327a54b5";
})
