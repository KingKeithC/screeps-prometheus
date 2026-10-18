{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
  };

  outputs = inputs:
    inputs.flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = (import (inputs.nixpkgs) { inherit system; });
      in
      {
        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Might need these later:
            #pnpm
            #nodejs
            #typescript
            #typescript-language-server
            python3
            uv
          ];
          shellHook = ''
	    uv sync
          '';
        };
      }
    );
}
