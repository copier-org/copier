# Get precommix from separate location, synced with last template update
import (builtins.fetchGit {
  url = "https://gitlab.com/moduon/precommix.git";
  ref = "main";
  rev = "3aa6083e1f2fa5aa7168da23c0e42e27b30097ff";
})
