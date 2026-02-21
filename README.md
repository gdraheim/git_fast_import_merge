[![Gitlab Status](https://gitlab.com/gdraheim/git_fast_import_merge/badges/main/pipeline.svg)](https://gitlab.com/gdraheim/git_fast_import_merge)
[![Code Coverage](https://img.shields.io/badge/29%20tests-92%25%20coverage-brightgreen)](https://github.com/gdraheim/git_fast_import_merge/blob/main/git_fast_import_merge.tests.py)
[![PyPI version](https://badge.fury.io/py/git_fast_import_merge.svg)](https://pypi.org/project/git_fast_import_merge/)


# git fast-import merge

The `git_fast_import_merge.py` tool can read multiple archive files from 'git fast-export' 
and merge them into a single archive file for 'git fast-import' ordering the changes by date. 

Optionally, (with -m) when switching the input file some 'merge' command is generated into 
the output archive file which makes for a history as if coming from multiple branches. This
works fine if the different archives do not really represent parallel developments.

## background

The tool was written for helper code that was shared in multiple different repositories.
Each project had its own necessities to add some changes to the code which were then 
synchronized to the other projects.

Now it is possible to use `git fast-export HEAD -- libcode.py libhelper.py > libcode1.fi`.

Then merge them like `./git_fast_import_merge.py libcode1.fi libcode2.fi -o libcode.fi`.

And the combined archive can be imported: `cd libbcode; cat ../libcode.fi | git fast-import`.

An example can be found here: https://github.com/gdraheim/tabtotext - extracted from
https://github.com/gdraheim/timetrack-odoo and two report-tool archives.

## updating a target repo

The basic execution assumes that you want to split off some files from a repo. So the
target repository is fresh and new.

If you want to add patches later then you need to provide two pieces of information:
the commit-hash of the target HEAD and the minimum DATE to consider from the inputs.

If you have a target repo then you can get that information like this:

* `git --no-pager rev-parse HEAD` # hash-of-commit
* `git --no-pager show -s --format=%cI HEAD` # date-of-commit

Provide these as `--head=hash-of-commit --date=date-of-commit`

If you say `--into=./path/to/workspace` then the tool will run these commands itself.
And adding `--import` then the fast-import will run on the into-workspace right-away.
However this is completely optional.

## skip and modify

Using glob patterns, it is possible to skip patches with `--skipsubject` and `--skipauthor`.

Using glob patterns, it is possible to set a new value with `--replaceauthor new=old`

if the glob pattern does not include `'*'` then it is considered a partial match
otherwise it becomes a full match, so you can decide to match and front or back.

## I take patches!

The code is doing what it had to do. There are surely some features missing.

Please create a ticket.... and dont' forget to create a testcase.

.... the usual checks for a Release are in [DEVGUIDE.MD](DEVGUIDE.MD)

