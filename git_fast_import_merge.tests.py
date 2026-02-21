#! /usr/bin/env python3
# pylint: disable=unused-variable,f-string-without-interpolation,missing-class-docstring,missing-function-docstring,invalid-name,consider-using-f-string,too-many-lines,line-too-long,multiple-statements
# pylint: disable=redefined-outer-name,broad-exception-caught,dangerous-default-value,unused-variable,redefined-builtin,bare-except,unspecified-encoding,missing-module-docstring

__copyright__ = "(C) 2023-2024 Guido Draheim, licensed under the Apache License 2.0"""
__version__ = "1.0.1321"

from typing import Optional, Any, List, Union, Iterator, NamedTuple, Mapping, Dict

from subprocess import check_output, Popen, PIPE, CalledProcessError
from unittest import TestCase, TestSuite, TextTestRunner
import os
import os.path as fs
import shutil
import sys
import re
import inspect
from time import sleep
from fnmatch import fnmatchcase as fnmatch
from logging import getLogger, basicConfig, WARNING, INFO, DEBUG, addLevelName

NOTE = (WARNING + INFO) // 2
HINT = (DEBUG + INFO) // 2
EXEC = NOTE + 1
TMP = NOTE + 2
addLevelName(HINT, "HINT")
addLevelName(NOTE, "NOTE")
addLevelName(EXEC, "EXEC")
addLevelName(TMP, "TMP")

SHOWGRAPH = HINT

logg = getLogger("TEST")
KEEP = 0
NIX = ""
GIT = "git"
RUN = "--no-pager"
PYTHON = "python3"
COVER = 0
MERGE = "git_fast_import_merge.py"
TESTDIR = "tmp"
COMMITHASH = "[0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h][0-9a-h]"
TIMEFORMAT = "[1-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][T.][0-9][0-9]:[0-9][0-9](:[0-9][0-9])?(Z|.*[+-][0-9][0-9])"


def sx__(cmd: str, cwd: Optional[str] = None, shell: bool = True, env: Mapping[str, str] = {"LANG": "C"}, **args: Any) -> str:
    try:
        return sh__(cmd, cwd=cwd, shell=shell, env=env, **args)
    except Exception as e:
        logg.debug("sh failed: %s", cmd)
        return ""


def sh__(cmd: str, cwd: Optional[str] = None, shell: bool = True, env: Mapping[str, str] = {"LANG": "C"}, **args: Any) -> str:
    logg.debug("sh %s", cmd)
    return decodes(check_output(cmd, cwd=cwd, shell=shell, env=env, **args))


class Run(NamedTuple):
    out: str
    err: str
    code: int


def sh(cmd: Union[str, List[str]], cwd: Optional[str] = None, shell: Optional[bool] = None,
       input: Optional[str] = None, env: Mapping[str, str] = {"LANG": "C"}) -> Run:
    std = run(cmd, cwd, shell, input, env)
    if std.code:
        raise CalledProcessError(std.code, cmd, std.out, std.err)
    return std


def run(cmd: Union[str, List[str]], cwd: Optional[str] = None, shell: Optional[bool] = None,
        input: Optional[str] = None, env: Mapping[str, str] = {"LANG": "C"}) -> Run:
    if isinstance(cmd, str):
        logg.log(EXEC, ": %s", cmd)
        shell = True if shell is None else shell
    else:
        logg.log(EXEC, ": %s", " ".join(["'%s'" % item for item in cmd]))
        shell = False if shell is None else shell
    if input is not None:
        run = Popen(cmd, cwd=cwd, shell=shell, stdout=PIPE,
                    stderr=PIPE, stdin=PIPE, env=env)
        out, err = run.communicate(input.encode("utf-8"))
    else:
        run = Popen(cmd, cwd=cwd, shell=shell,
                    stdout=PIPE, stderr=PIPE, env=env)
        out, err = run.communicate()
    text_out = decodes(out)
    text_err = decodes(err)
    logg.debug("stdout = %s", text_out.splitlines())
    if text_err:
        logg.log(HINT, " stderr = %s", text_err.splitlines())
    if run.returncode:
        logg.log(HINT, " return = %s", run.returncode)
    return Run(text_out, text_err, run.returncode)


def decodes(text: Union[bytes, str]) -> str:
    if text is None:
        return None
    if isinstance(text, bytes):
        encoded = sys.getdefaultencoding()
        if encoded in ["ascii"]:
            encoded = "utf-8"
        try:
            return text.decode(encoded)
        except:
            return text.decode("latin-1")
    return text


def sh_cat(filename: str, default: str = NIX, cwd: str = NIX) -> Run:
    if cwd:
        filepath = fs.join(cwd, filename)
    else:
        filepath = filename
    if not fs.exists(filepath):
        logg.log(EXEC, "  cat %s  # does not exist", filename)
        return Run(default, "does not exist: " + filename, 3)
    else:
        text = open(filepath).read()
        lines = text.splitlines()
        logg.log(EXEC, "  cat %s  # [%s bytes] [%s lines]", filename, len(
            text), len(lines))
        logg.debug("%s", lines)
        return Run(text, "", 0)


def _lines(lines: Union[str, List[str]]) -> List[str]:
    if isinstance(lines, str):
        xlines = lines.split("\n")
        if len(xlines) and xlines[-1] == "":
            xlines = xlines[:-1]
        return xlines
    return lines


def lines(text: Union[str, List[str]]) -> List[str]:
    lines = []
    for line in _lines(text):
        lines.append(line.rstrip())
    return lines


def grep(pattern: str, lines: Union[str, List[str]]) -> Iterator[str]:
    for line in _lines(lines):
        if re.search(pattern, line.rstrip()):
            yield line.rstrip()


def greps(lines: Union[str, List[str]], pattern: str) -> List[str]:
    return list(grep(pattern, lines))


def greplines(lines: Union[str, List[str]], *pattern: str) -> List[str]:
    eachline = [line.rstrip() for line in _lines(lines) if line.rstrip()]
    if not pattern:
        logg.info("[*]=> %s", eachline)
        return eachline
    found = []
    done = len(pattern)
    look = 0
    if done == 1 and pattern[0] == "" and not eachline:
        return ["EMPTY"]
    for line in eachline:
        if not pattern[look]:
            if not line.strip():
                found.append(line)
                look += 1
                if look == done:
                    return found
        else:
            if re.search(pattern[look], line.rstrip()):
                found.append(line)
                look += 1
                if look == done:
                    return found
    logg.debug("[?]<< %s", pattern)
    logg.debug("[?]=> %s", eachline)
    return []

def loadworkspace(workspace: str, keeplinebreaks: bool = False) -> Dict[str, List[str]]:
    files: Dict[str, List[str]] = {}
    for dirpath, dirnames, filenames in os.walk(workspace):
        if "/.git/" in ("/" + dirpath + "/"):
            continue
        for name in filenames:
            filename = fs.join(dirpath, name)
            workname = filename[len(workspace) + 1:]
            logg.log(DEBUG, " wc '%s'", workname)
            text = decodes(open(filename).read())
            files[workname] = text.splitlines(keeplinebreaks)
            info = files[workname] if len(text) < 30 else ["%s bytes" % len(text)]
            logg.log(EXEC, "  wc '%s': %s", workname, info)
    return files

def get_caller_name() -> str:
    frame = inspect.currentframe().f_back.f_back  # type: ignore
    return frame.f_code.co_name  # type: ignore


def get_caller_caller_name() -> str:
    frame = inspect.currentframe().f_back.f_back.f_back  # type: ignore
    return frame.f_code.co_name  # type: ignore


class ImportMergeTest(TestCase):
    def caller_testname(self) -> str:
        name = get_caller_caller_name()
        x1 = name.find("_")
        if x1 < 0:
            return name
        x2 = name.find("_", x1 + 1)
        if x2 < 0:
            return name
        return name[:x2]

    def testname(self, suffix: Optional[str] = None) -> str:
        name = self.caller_testname()
        if suffix:
            return name + "_" + suffix
        return name

    def testdir(self, testname: Optional[str] = None, keep: bool = False) -> str:
        testname = testname or self.caller_testname()
        newdir = fs.join(TESTDIR, testname)
        if fs.isdir(newdir) and not keep:
            shutil.rmtree(newdir)
        if not fs.isdir(newdir):
            os.makedirs(newdir)
            logg.log(TMP, "==================== %s", newdir)
        return newdir

    def rm_testdir(self, testname: Optional[str] = None) -> str:
        testname = testname or self.caller_testname()
        newdir = fs.join(TESTDIR, testname)
        if fs.isdir(newdir):
            testcoverage = fs.join(newdir, ".coverage")
            savecoverage = fs.join(TESTDIR, F"{testname}.coverage")
            if fs.exists(testcoverage):
                logg.debug("%s -> %s", testcoverage, savecoverage)
                os.replace(testcoverage, savecoverage)
            if not KEEP:
                shutil.rmtree(newdir)
            else:
                logg.log(TMP, "================ KEEP %s", newdir)
        return newdir
    def cover(self) -> str:
        return F"{PYTHON} -m coverage run" if COVER else F"{PYTHON}"
    def test_010(self) -> None:
        tmp = self.testdir()
        cover = self.cover()
        tests = __file__.replace(".tests.py", ".test.py")
        execs = fs.relpath(tests, tmp)
        std = sh(F"{cover} {execs} -v time_from", cwd=tmp)
        logg.log(EXEC, ">>\n%s", std.err)
        self.rm_testdir()
    def test_020(self) -> None:
        tmp = self.testdir()
        cover = self.cover()
        tests = __file__.replace(".tests.py", ".test.py")
        execs = fs.relpath(tests, tmp)
        std = sh(F"{cover} {execs} -v commit_from", cwd=tmp)
        logg.log(EXEC, ">>\n%s", std.err)
        self.rm_testdir()
    def test_100(self) -> None:
        """ import to empty repo"""
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *2"))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["hello"], }
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_110(self) -> None:
        """ import to empty repo - with third commit"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertFalse(greplines(catN.out, "merge :"))  # !
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *3"))
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_120(self) -> None:
        """ import to empty repo - with third commit - show as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertTrue(greplines(catN.out, "merge :"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *3"))
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertTrue(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_130(self) -> None:
        """ import to empty repo - rename into subdir - show as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --merge --subdir travel", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertTrue(greplines(catN.out, "merge :"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *3"))
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertTrue(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"travel/world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_150(self) -> None:
        """ import to empty repo - with third commit -- replaceauthor B"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --replaceauthor 'Mr.B=Mrs.B <user@B>'", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertFalse(greplines(catN.out, "merge :"))  # !
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *3"))
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mrs.B", "Mr.A"))
        self.assertFalse(greplines(log.out, "Mr.B"))
        self.assertTrue(greplines(log.out, "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_160(self) -> None:
        """ import to empty repo - with third commit - skip user@B"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --skipauthor=Mr.B", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A"))
        self.assertFalse(greplines(catN.out, "hello-B"))  # !
        self.assertFalse(greplines(catN.out, "merge :"))  # !
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *2"))  # !!
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-A"))
        self.assertFalse(greplines(log.out, "hello-B"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_170(self) -> None:
        """ import to empty repo - .. - skip user@B - try as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --skipauthor=Mr.B --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", ))
        self.assertFalse(greplines(catN.out, "hello-B"))
        self.assertFalse(greplines(catN.out, "merge :"))  # no merge anymore needed
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *2"))  # !
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-A"))
        self.assertFalse(greplines(log.out, "hello-B"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))  # no merge anymore needed
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_180(self) -> None:
        """ import to empty repo - .. - skip subject B - try as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --skipsubject=hello-B --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", ))
        self.assertFalse(greplines(catN.out, "hello-B"))
        self.assertFalse(greplines(catN.out, "merge :"))  # no merge anymore needed
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *2"))  # !
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-A"))
        self.assertFalse(greplines(log.out, "hello-B"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))  # no merge anymore needed
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_190(self) -> None:
        """ import to empty repo - .. - skip subject again - try as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --skipsubject=again --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B",))
        self.assertFalse(greplines(catN.out, "merge :"))  # no merge anymore needed
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *2"))  # !
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))  # no merge anymore needed
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["hello"], }  # no more "again"
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_200(self) -> None:
        """ import to non-empty repo (GitHub likes to setup LICENSE)"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat("B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo OK > LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m license LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, "main .* license"))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --head {head}", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, ""))
        catN = sh_cat("N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *2"))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-B", "hello-A", "license"))
        self.assertTrue(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["hello"], 'LICENSE': ['OK']}
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_210(self) -> None:
        """ import to non-empty repo - with third commit"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat("B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo OK > LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m license LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, "main .* license"))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --head {head}", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, ""))
        catN = sh_cat("N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *3"))
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        self.assertNotEqual(head, std.out.strip())
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "hello-B", "hello-A", "license"))
        self.assertTrue(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], 'LICENSE': ['OK']}
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_220(self) -> None:
        """ import to non-empty repo - with third commit - show as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat("B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo OK > LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m license LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, "main .* license"))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --head {head} --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, ""))
        catN = sh_cat("N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *3"))
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        self.assertNotEqual(head, std.out.strip())
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "hello-B", "hello-A", "license"))
        self.assertTrue(greplines(log.out, "license"))
        self.assertTrue(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], 'LICENSE': ['OK']}
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_230(self) -> None:
        """ import to non-empty repo - rename to subdir - show as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat("B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo OK > LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m license LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, "main .* license"))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --head {head} --merge --subdir travel", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, ""))
        catN = sh_cat("N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *3"))
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        self.assertNotEqual(head, std.out.strip())
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "hello-B", "hello-A", "license"))
        self.assertTrue(greplines(log.out, "license"))
        self.assertTrue(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"travel/world.txt": ["again"], 'LICENSE': ['OK']}
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_250(self) -> None:
        """ import to non-empty repo - with third commit"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat("B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo OK > LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m license LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, "main .* license"))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --head {head} --replaceauthor 'Mr.B=Mrs.B <user@B>' ", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, ""))
        catN = sh_cat("N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *3"))
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        self.assertNotEqual(head, std.out.strip())
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mrs.B", "Mr.A"))
        self.assertFalse(greplines(log.out, "Mr.B"))
        self.assertTrue(greplines(log.out, "hello-B", "hello-A", "license"))
        self.assertTrue(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], 'LICENSE': ['OK']}
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_260(self) -> None:
        """ import to non-empty repo - with third commit - skipauthor B"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat("B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo OK > LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m license LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, "main .* license"))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --head {head} --skipauthor=Mr.B ", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, ""))
        catN = sh_cat("N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A"))
        self.assertFalse(greplines(catN.out, "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *2"))  # !
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        self.assertNotEqual(head, std.out.strip())
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-A", "license"))
        self.assertFalse(greplines(log.out, "hello-B"))
        self.assertTrue(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], 'LICENSE': ['OK']}
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_270(self) -> None:
        """ import to non-empty repo - ... - skipauthor B - try as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat("B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo OK > LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m license LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, "main .* license"))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --head {head} --skipauthor=Mr.B --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, ""))
        catN = sh_cat("N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A"))
        self.assertFalse(greplines(catN.out, "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *2"))  # !
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        self.assertNotEqual(head, std.out.strip())
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-A", "license"))
        self.assertFalse(greplines(log.out, "hello-B"))
        self.assertTrue(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))  # not needed anymore
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], 'LICENSE': ['OK']}
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_280(self) -> None:
        """ import to non-empty repo - ... - skipsubject B - try as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat("B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo OK > LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m license LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, "main .* license"))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --head {head} --skipsubject=hello-B --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, ""))
        catN = sh_cat("N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A"))
        self.assertFalse(greplines(catN.out, "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *2"))  # !
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        self.assertNotEqual(head, std.out.strip())
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-A", "license"))
        self.assertFalse(greplines(log.out, "hello-B"))
        self.assertTrue(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))  # not needed anymore
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], 'LICENSE': ['OK']}
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_290(self) -> None:
        """ import to non-empty repo - ... - skipsubject again - try as --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat("B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo OK > LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m license LICENSE", cwd=N)
        self.assertTrue(greplines(std.out, "main .* license"))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --head {head} --skipsubject=again --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, ""))
        catN = sh_cat("N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        self.assertTrue(greplines(std.err, "commits: *2"))  # !
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        self.assertNotEqual(head, std.out.strip())
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "hello-B", "hello-A", "license"))
        self.assertTrue(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))  # not needed anymore
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["hello"], 'LICENSE': ['OK']}
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_300(self) -> None:
        """ import to empty repo - with third repo"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        C = fs.join(tmp, "C")
        std = sh(F"{git} init -b main C", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.C && {git} config user.email user@C", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'wonderful' > world.txt", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-C world.txt", cwd=C)
        self.assertTrue(greplines(std.out, "main .* hello-C"))
        std = sh(F"{git} log", cwd=C)
        self.assertTrue(greplines(std.out, "commit ", " hello-C"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        std = sh(F"{git} fast-export HEAD > ../C.fi", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        catC = sh_cat(F"C.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi C.fi -o N.fi", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertFalse(greplines(catN.out, "merge :"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *4"))
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mr.C", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "hello-C", "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_310(self) -> None:
        """ import to empty repo - with third repo - with --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        C = fs.join(tmp, "C")
        std = sh(F"{git} init -b main C", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.C && {git} config user.email user@C", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'wonderful' > world.txt", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-C world.txt", cwd=C)
        self.assertTrue(greplines(std.out, "main .* hello-C"))
        std = sh(F"{git} log", cwd=C)
        self.assertTrue(greplines(std.out, "commit ", " hello-C"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        std = sh(F"{git} fast-export HEAD > ../C.fi", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        catC = sh_cat(F"C.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi C.fi -o N.fi --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertTrue(greplines(catN.out, "merge :"))  # ..
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *4"))
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mr.C", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "hello-C", "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertTrue(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_320(self) -> None:
        """ import to empty repo - with third repo - with --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        C = fs.join(tmp, "C")
        std = sh(F"{git} init -b main C", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.C && {git} config user.email user@C", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'wonderful' > world.txt", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-C world.txt", cwd=C)
        self.assertTrue(greplines(std.out, "main .* hello-C"))
        std = sh(F"{git} log", cwd=C)
        self.assertTrue(greplines(std.out, "commit ", " hello-C"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        std = sh(F"{git} fast-export HEAD > ../C.fi", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        catC = sh_cat(F"C.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        std = sh(F"echo 'skipauthor=Mr.A' > merge.opt", cwd=tmp)
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi C.fi -o N.fi --merge -@ merge.opt", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-B"))
        self.assertFalse(greplines(catN.out, "hello-A"))
        self.assertFalse(greplines(catN.out, "merge :"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *2"))  # two less
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.C", "Mr.B"))
        self.assertFalse(greplines(log.out, "Mr.A"))
        self.assertTrue(greplines(log.out, "hello-B"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["wonderful"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_330(self) -> None:
        """ import to empty repo - with third repo - with --merge"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        C = fs.join(tmp, "C")
        std = sh(F"{git} init -b main C", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.C && {git} config user.email user@C", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'wonderful' > world.txt", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-C world.txt", cwd=C)
        self.assertTrue(greplines(std.out, "main .* hello-C"))
        std = sh(F"{git} log", cwd=C)
        self.assertTrue(greplines(std.out, "commit ", " hello-C"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        std = sh(F"{git} fast-export HEAD > ../C.fi", cwd=C)
        self.assertTrue(greplines(std.out, ""))
        catC = sh_cat(F"C.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        std = sh(F"echo 'skipauthor=Mr.B' > merge.opt", cwd=tmp)
        std = sh(F"echo 'skipauthor=Mr.C' >> merge.opt", cwd=tmp)
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi C.fi -o N.fi --merge -@ merge.opt", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A"))
        self.assertFalse(greplines(catN.out, "hello-B"))
        self.assertFalse(greplines(catN.out, "merge :"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *2"))  # two less
        self.assertTrue(greplines(std.out, ""))
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.A", "Mr.A"))
        self.assertFalse(greplines(log.out, "Mr.B"))
        self.assertFalse(greplines(log.out, "Mr.C"))
        self.assertTrue(greplines(log.out, "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertFalse(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["again"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_400(self) -> None:
        """ import to empty repo - with third commit - and update fourth commit --into"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertTrue(greplines(catN.out, "merge :"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *3"))
        self.assertTrue(greplines(std.out, ""))
        #
        sleep(2)
        #
        std = sh(F"echo 'updated' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m update-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* update-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " update-B"))
        #
        std = sh(F"{git} fast-export HEAD > ../B2.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB2 = sh_cat(F"B2.fi", cwd=tmp)
        self.assertTrue(greplines(catB2.out, "hello-B"))
        self.assertTrue(greplines(catB2.out, "update-B"))
        #
        std = sh(F"{cover} {merge} A.fi B2.fi -o N2.fi --merge --into=N", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN2 = sh_cat(F"N2.fi", cwd=tmp)
        logg.warning("catN2\n%s", catN2.out)
        logg.warning("catN2 = %s", greplines(catN2.out, "hello-A", "hello-B"))
        self.assertFalse(greplines(catN2.out, "hello-A", "hello-B"))  # skipped old patches
        self.assertFalse(greplines(catN2.out, "merge :"))  # and 'updated' has no merge
        #
        std = sh(F"{git} fast-import < ../N2.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *1"))  # only the 'updated'
        self.assertTrue(greplines(std.out, ""))
        #
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.B", "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "update-B", "again", "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertTrue(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["updated"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_420(self) -> None:
        """ import to empty repo - four commits - with update --into --import"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertTrue(greplines(catN.out, "merge :"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *3"))
        self.assertTrue(greplines(std.out, ""))
        #
        sleep(2)
        #
        std = sh(F"echo 'updated' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m update-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* update-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " update-B"))
        #
        std = sh(F"{git} fast-export HEAD > ../B2.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB2 = sh_cat(F"B2.fi", cwd=tmp)
        self.assertTrue(greplines(catB2.out, "hello-B"))
        self.assertTrue(greplines(catB2.out, "update-B"))
        #
        std = sh(F"{cover} {merge} A.fi B2.fi --import --merge --into=N", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        # there is an implicit N.fi here for the automated fast-import
        #
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.B", "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "update-B", "again", "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertTrue(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["updated"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_430(self) -> None:
        """ import to empty repo - check historylog - with update --into --import"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --merge --historyfile=N.log", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertTrue(greplines(catN.out, "merge :"))
        logN = sh_cat(F"N.log", cwd=tmp)
        logg.info("merge1>>\n%s", logN.out)
        self.assertTrue(greplines(logN.out, ": again", ": hello-B", ": hello-A"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *3"))
        self.assertTrue(greplines(std.out, ""))
        #
        sleep(2)
        #
        std = sh(F"echo 'updated' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m update-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* update-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " update-B"))
        #
        std = sh(F"{git} fast-export HEAD > ../B2.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB2 = sh_cat(F"B2.fi", cwd=tmp)
        self.assertTrue(greplines(catB2.out, "hello-B"))
        self.assertTrue(greplines(catB2.out, "update-B"))
        #
        std = sh(F"{cover} {merge} A.fi B2.fi --import --merge --into=N --historylog", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        # there is an implicit N.fi here for the automated fast-import
        logg.info("merge2>>\n%s", std.err)
        self.assertTrue(std.err, "commits: *1")
        self.assertTrue(std.err, "DONE:MERGE:.*: update-B")
        #
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.B", "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "update-B", "again", "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertTrue(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["updated"], }
        self.assertEqual(wants, files)
        self.rm_testdir()
    def test_450(self) -> None:
        """ import to empty repo - with third commit - and update fourth commit OFFLINE"""
        py = F"{PYTHON}"
        git = F"{GIT} {RUN}"
        tmp = self.testdir()
        A = fs.join(tmp, "A")
        std = sh(F"{git} init -b main A", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.A && {git} config user.email user@A", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-A world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* hello-A"))
        std = sh(F"{git} log", cwd=A)
        self.assertTrue(greplines(std.out, "commit ", " hello-A"))
        #
        sleep(2)
        #
        B = fs.join(tmp, "B")
        std = sh(F"{git} init -b main B", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty Git repository"))
        std = sh(F"{git} config user.name Mr.B && {git} config user.email user@B", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"echo 'hello' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m hello-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* hello-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " hello-B"))
        #
        sleep(2)
        #
        std = sh(F"echo 'again' > world.txt", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m again world.txt", cwd=A)
        self.assertTrue(greplines(std.out, "main .* again"))
        #
        std = sh(F"{git} fast-export HEAD > ../A.fi", cwd=A)
        self.assertTrue(greplines(std.out, ""))
        catA = sh_cat(F"A.fi", cwd=tmp)
        self.assertTrue(greplines(catA.out, "hello-A"))
        std = sh(F"{git} fast-export HEAD > ../B.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB = sh_cat(F"B.fi", cwd=tmp)
        self.assertTrue(greplines(catB.out, "hello-B"))
        self.assertNotEqual(greplines(catA.out, "committer .*"),
                            greplines(catB.out, "committer .*"))
        #
        N = fs.join(tmp, "N")
        std = sh(F"{git} init -b main N", cwd=tmp)
        self.assertTrue(greplines(std.out, "Initialized empty"))
        std = sh(F"{git} config user.name Mr.N && {git} config user.email user@N", cwd=N)
        self.assertTrue(greplines(std.out, ""))
        #
        merge = fs.relpath(MERGE, tmp)
        cover = self.cover()
        std = sh(F"{cover} {merge} A.fi B.fi -o N.fi --merge", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN = sh_cat(F"N.fi", cwd=tmp)
        self.assertTrue(greplines(catN.out, "hello-A", "hello-B"))
        self.assertTrue(greplines(catN.out, "merge :"))
        #
        std = sh(F"{git} fast-import < ../N.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *3"))
        self.assertTrue(greplines(std.out, ""))
        #
        sleep(2)
        #
        std = sh(F"echo 'updated' > world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} add world.txt", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        std = sh(F"{git} commit -m update-B world.txt", cwd=B)
        self.assertTrue(greplines(std.out, "main .* update-B"))
        std = sh(F"{git} log", cwd=B)
        self.assertTrue(greplines(std.out, "commit ", " update-B"))
        #
        std = sh(F"{git} fast-export HEAD > ../B2.fi", cwd=B)
        self.assertTrue(greplines(std.out, ""))
        catB2 = sh_cat(F"B2.fi", cwd=tmp)
        self.assertTrue(greplines(catB2.out, "hello-B"))
        self.assertTrue(greplines(catB2.out, "update-B"))
        #
        std = sh(F"{git} rev-parse HEAD", cwd=N)
        self.assertTrue(greplines(std.out, COMMITHASH))
        head = std.out.strip()
        std = sh(F"{git} show -s --format=%cI HEAD", cwd=N)
        logg.warning("show -s\n%s", std.out)
        self.assertTrue(greplines(std.out, TIMEFORMAT))
        date = std.out.strip()
        std = sh(F"{cover} {merge} A.fi B2.fi -o N2.fi --merge --head={head} --date={date}", cwd=tmp)
        self.assertTrue(greplines(std.out, ""))
        catN2 = sh_cat(F"N2.fi", cwd=tmp)
        self.assertFalse(greplines(catN2.out, "hello-A", "hello-B"))  # skipped old patches
        self.assertFalse(greplines(catN2.out, "merge :"))  # and 'updated' has no merge
        #
        std = sh(F"{git} fast-import < ../N2.fi", cwd=N)
        self.assertTrue(greplines(std.err, "commits: *1"))  # only the 'updated'
        self.assertTrue(greplines(std.out, ""))
        #
        log = sh(F"{git} log --graph", cwd=N)
        logg.log(SHOWGRAPH, ">>>\n%s", log.out)
        self.assertTrue(greplines(log.out, "Mr.B", "Mr.A", "Mr.B", "Mr.A"))
        self.assertTrue(greplines(log.out, "update-B", "again", "hello-B", "hello-A"))
        self.assertFalse(greplines(log.out, "license"))
        self.assertTrue(greplines(log.out, "Merge:"))
        #
        M = fs.join(tmp, "M")
        out = sh(F"{git} clone --local N M", cwd=tmp)
        files = loadworkspace(M)
        wants = {"world.txt": ["updated"], }
        self.assertEqual(wants, files)
        self.rm_testdir()

    def test_999(self) -> None:
        if not COVER: self.skipTest("no --cover enabled")
        merge = fs.relpath(MERGE, TESTDIR)
        coverage = F"{PYTHON} -m coverage"
        std = sh(F"{coverage} combine *.coverage", cwd=TESTDIR)
        std = sh(F"{coverage} annotate {merge}", cwd=TESTDIR)
        std = sh(F"{coverage} report {merge}", cwd=TESTDIR)
        print(std.out)

if __name__ == "__main__":
    # unittest.main()
    from optparse import OptionParser # pylint: disable=deprecated-module
    cmdline = OptionParser("%s test...")
    cmdline.add_option("-v", "--verbose", action="count",
                       default=0, help="more verbose logging")
    cmdline.add_option("-^", "--quiet", action="count",
                       default=0, help="less verbose logging")
    cmdline.add_option("--script1", metavar=MERGE)
    cmdline.add_option("--git", metavar=GIT)
    cmdline.add_option("--python", metavar=PYTHON, default=PYTHON)
    cmdline.add_option("-C", "--cover", action="count", default=0,
                       help="make {script},cover [%default]")
    cmdline.add_option("-k", "--keep", action="count",
                       default=0, help="keep testdir = ./tmp/{testname}/")
    cmdline.add_option("-S", "--showgraph", action="count", default=0,
                       help="Show the final log-graph on each test. [%default]")
    cmdline.add_option("--failfast", action="store_true", default=False,
                       help="Stop the test run on the first error or failure.")
    cmdline.add_option("--xmlresults", metavar="FILE", default=None,
                       help="capture results as a junit xml file [%default]")
    opt, args = cmdline.parse_args()
    basicConfig(level=max(0, WARNING - 5 * opt.verbose + 10 * opt.quiet))
    KEEP = opt.keep
    if opt.showgraph:
        SHOWGRAPH = EXEC
    MERGE = opt.script1 or MERGE
    GIT = opt.git or GIT
    PYTHON = opt.python or PYTHON
    COVER = opt.cover
    #
    if not args:
        args = ["test_*"]
    suite = TestSuite()
    for arg in args:
        if len(arg) > 2 and arg[0].isalpha() and arg[1] == "_":
            arg = "test_" + arg[2:]
        for classname in sorted(globals()):
            if not classname.endswith("Test"):
                continue
            testclass = globals()[classname]
            for method in sorted(dir(testclass)):
                if "*" not in arg:
                    arg += "*"
                if arg.startswith("_"):
                    arg = arg[1:]
                if fnmatch(method, arg):
                    suite.addTest(testclass(method))
    # running
    xmlresults = None
    if opt.xmlresults:
        if os.path.exists(opt.xmlresults):
            os.remove(opt.xmlresults)
        xmlresults = open(opt.xmlresults, "wb")
    if xmlresults:
        import xmlrunner  # type: ignore[import-untyped]
        Runner = xmlrunner.XMLTestRunner
        result = Runner(xmlresults).run(suite)
        logg.info(" XML reports written to %s", opt.xmlresults)
    else:
        Runner = TextTestRunner
        result = Runner(verbosity=opt.verbose,
                        failfast=opt.failfast).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
