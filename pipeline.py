import time
import os
import os.path
import shutil
import glob
from distutils.version import StrictVersion

import seesaw
from seesaw.project import *
from seesaw.config import *
from seesaw.item import *
from seesaw.task import *
from seesaw.pipeline import *
from seesaw.externalprocess import *
from seesaw.tracker import *


if StrictVersion(seesaw.__version__) < StrictVersion("0.0.5"):
  raise Exception("This pipeline needs seesaw version 0.0.5 or higher.")


USER_AGENT = "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27"
VERSION = "20121009.01"

class PrepareDirectories(SimpleTask):
  def __init__(self):
    SimpleTask.__init__(self, "PrepareDirectories")

  def process(self, item):
    item_name = item["item_name"]
    dirname = "/".join(( item["data_dir"], item_name ))

    if os.path.isdir(dirname):
      shutil.rmtree(dirname)

    os.makedirs(dirname + "/files")

    item["item_dir"] = dirname
    item["warc_file_base"] = "btinternet.com-user-%s-%s" % (item_name, time.strftime("%Y%m%d-%H%M%S"))

class MoveFiles(SimpleTask):
  def __init__(self):
    SimpleTask.__init__(self, "MoveFiles")

  def process(self, item):
    os.rename("%(item_dir)s/%(warc_file_base)s.warc.gz" % item,
              "%(data_dir)s/%(warc_file_base)s.warc.gz" % item)

    shutil.rmtree("%(item_dir)s" % item)


project = Project(
  title = "Webshots",
  project_html = """
    <img class="project-logo" alt="BT logo" src="http://archiveteam.org/images/thumb/4/4b/BT_Logo_1.jpg/120px-BT_Logo_1.jpg" />
    <h2>BT Internet homepages<span class="links"><a href="http://www.google.com/search?q=site:btinternet.co.uk">Search sites on Google</a> &middot; <a href="http://tracker.archiveteam.org/btinternet/">Leaderboard</a></span></h2>
    <p>BT is closing its free web hosting service.</p>
  """,
  utc_deadline = datetime.datetime(2012,10,31, 23,59,0)
)

pipeline = Pipeline(
  GetItemFromTracker("http://tracker.archiveteam.org/btinternet", downloader, VERSION),
  PrepareDirectories(),
  WgetDownload([ "./wget-lua",
      "-U", USER_AGENT,
      "-nv",
      "-o", ItemInterpolation("%(item_dir)s/wget.log"),
      "--directory-prefix", ItemInterpolation("%(item_dir)s/files"),
      "--force-directories",
      "--adjust-extension",
      "-e", "robots=off",
      "--page-requisites",
      "-r", "-l", "inf", "--no-remove-listing",
      "--no-parent",
      "--lua-script", "stats.lua",
      "--reject-regex", "\\.html?/|cgi-bin/counter",
      "--timeout", "30",
      "--tries", "10",
      "--waitretry", "5",
      "--warc-file", ItemInterpolation("%(item_dir)s/%(warc_file_base)s"),
      "--warc-header", "operator: Archive Team",
      "--warc-header", "btinternet-dld-script-version: " + VERSION,
      "--warc-header", ItemInterpolation("btinternet-username: %(item_name)s"),
      ItemInterpolation("http://www.btinternet.com/~%(item_name)s/"),
      ItemInterpolation("http://www.%(item_name)s.btinternet.co.uk/")
    ],
    max_tries = 2,
    accept_on_exit_code = [ 0, 6, 8 ],
  ),
  PrepareStatsForTracker(
    defaults = { "downloader": downloader, "version": VERSION },
    file_groups = {
      "data": [ ItemInterpolation("%(item_dir)s/%(warc_file_base)s.warc.gz") ]
    }
  ),
  MoveFiles(),
  LimitConcurrent(NumberConfigValue(min=1, max=4, default="1", name="shared:rsync_threads", title="Rsync threads", description="The maximum number of concurrent uploads."),
    RsyncUpload(
      target = ConfigInterpolation("fos.textfiles.com::alardland/warrior/btinternet/%s/", downloader),
      target_source_path = ItemInterpolation("%(data_dir)s/"),
      files = [
        ItemInterpolation("%(warc_file_base)s.warc.gz")
      ],
      extra_args = [
        "--partial",
        "--partial-dir", ".rsync-tmp"
      ]
    ),
  ),
  SendDoneToTracker(
    tracker_url = "http://tracker.archiveteam.org/btinternet",
    stats = ItemValue("stats")
  )
)

