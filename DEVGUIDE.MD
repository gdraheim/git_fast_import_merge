# RELEASE PROCESS

* `make type`
* `make style`
* `make check`
* `make coverage`
* update README.md mit coverage & testnumber
* `make pkg` # running -m build
* `make ins` # make install
* `make show`
* `make uns` # make uinstall
* `make version`
  * git commit -m v...
* `make inst
* `make show`
* `make uns`
* `git push` 
* wait for gitlab-ci / github-workflows to finish
* `make tag`
  * git tag v..... 
* `make build`
   * twine...
* `git push --tags`
