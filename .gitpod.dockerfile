FROM gitpod/workspace-full
USER gitpod
RUN nix-channel --update
RUN nix-env -f '<nixpkgs>' -iA nix cacert direnv direnv-nix
RUN echo "source $HOME/.nix-profile/share/nix-direnv/direnvrc" >> $HOME/.direnvrc
RUN echo 'eval "$(direnv hook bash)"' >> $HOME/.bashrc
