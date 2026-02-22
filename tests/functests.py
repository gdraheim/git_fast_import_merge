#! /usr/bin/env python3

__copyright__ = "(C) 2023-2026 Guido Draheim, licensed under the Apache License 2.0"""
__version__ = "1.1.3077"

from unittest import main, TestCase
from src import git_fast_import_merge as app

tz1 = app.TimeZone(app.Plus(hours=1))
utc = app.TimeZone.utc
class time_from(TestCase):
   def test_010(self) -> None:
      have = app.time_from("foo")
      want = None
      self.assertEqual(want, have)
   def test_011(self) -> None:
      have = app.time_from("2022-12-01T23:34:45 +01:00")
      want = app.Time(2022,12,1, 23, 34, 45, tzinfo=tz1)
      self.assertEqual(want, have)
   def test_012(self) -> None:
      have = app.time_from("2022-12-01.23:34:45 +01:00")
      want = app.Time(2022,12,1, 23, 34, 45, tzinfo=tz1)
      self.assertEqual(want, have)
   def test_013(self) -> None:
      have = app.time_from("2022-12-01.23:34:45")
      want = app.Time(2022,12,1, 23, 34, 45, tzinfo=utc)
      self.assertEqual(want, have)
   def test_014(self) -> None:
      have = app.time_from("2022-12-01Z23:34:45")
      want = app.Time(2022,12,1, 23, 34, 45, tzinfo=utc)
      self.assertEqual(want, have)
   def test_015(self) -> None:
      want = app.Time(2022,12,1, 23, 34, 45, tzinfo=tz1)
      time = want.timestamp()
      spec = "%s +00:00" % int(time)
      have = app.time_from(spec)
      self.assertEqual(want, have)
   def test_016(self) -> None:
      want = app.Time(2022,12,1, 23, 34, 45, tzinfo=utc)
      time = want.timestamp()
      spec = "%s +01:00" % int(time)
      have = app.time_from(spec)
      self.assertEqual(want, have)
   def test_019(self) -> None:
      try:
          have = app.with_time_from("foo")
          self.fail("should throw")
      except Exception as e:
          self.assertIn("not a time spec", str(e))

class commit_from(TestCase):
   def test_020(self) -> None:
       blob = ["commit refs/heads/main", "mark :2", 
               "author Mr.A <user@A> 1722770218 +0200",
               "committer Mr.A <user@A> 1722770218 +0200",
               "data 6", "hello", "M 100644 :1 world.txt"]
       have = app.commit_from(app.Blob(app.Fromfile("X", "test"), "commit", "", "\n".join(blob)))
   def test_021(self) -> None:
       blob = ["commit refs/heads/main", "mark :2", "merge :1",
               "author Mr.A <user@A> 1722770218 +0200",
               "committer Mr.A <user@A> 1722770218 +0200",
               "data 6", "hello", "M 100644 :1 world.txt"]
       have = app.commit_from(app.Blob(app.Fromfile("X", "test"), "commit", "", "\n".join(blob)))
   def test_022(self) -> None:
       blob = ["commit refs/heads/main", "mark :2", 
               "author Mr.A <user@A> 1722770218 +0200",
               "committer Mr.A <user@A> 1722770218 +0200",
               "data 6", "hello", "M 100644 :1 world.txt",
               "merge :1",]
       have = app.commit_from(app.Blob(app.Fromfile("X", "test"), "commit", "", "\n".join(blob)))
   def test_028(self) -> None:
       blob = ["commit refs/heads/main", "mark :2", "foobar :1",
               "author Mr.A <user@A> 1722770218 +0200",
               "committer Mr.A <user@A> 1722770218 +0200",
               "data 6", "hello", "M 100644 :1 world.txt",
               "fubar :1",]
       have = app.commit_from(app.Blob(app.Fromfile("X", "test"), "commit", "", "\n".join(blob)))
   def test_029(self) -> None:
       blob = ["commit refs/heads/main", "mark :2", 
               "author Mr.A <user@A> 1722770218 +0200",
               "committer Mr.A <user@A> 1722770218 +0200",
               "data 6", "hello", "M 100644 :1 world.txt",
               "fubar :1",]
       have = app.commit_from(app.Blob(app.Fromfile("X", "test"), "commit", "", "\n".join(blob)))


if __name__ == "__main__":
   main()

