# NBX-DEUX

Attempt at porting `dalejung/nbx` over the version 7 of notebook.

Porting to Notebook 7 FE seems like a deadend atm. Trying `nbclassic` 

https://github.com/dalejung/nbclassic/tree/nbx_patch

```
cd nbx_deux/nbextensions

jupyter nbclassic-extension install --symlink --user ./nbx-vim
jupyter nbclassic-extension enable nbx-vim/vim --user

jupyter nbclassic-extension install --symlink --user ./nbx-gist
jupyter nbclassic-extension enable nbx-gist/gist --user
```
