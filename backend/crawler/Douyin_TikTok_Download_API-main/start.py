# Copyright (C) 2021 Evil0ctal
#
#
# You may obtain a copy of the License at:
# http://www.apache.org/licenses/LICENSE-2.0
#
# limitations under the License.
# 　　　　 　　  ＿＿
# 　　　 　　 ／＞　　フ
# 　　　 　　| 　_　 _ l
# 　 　　 　／` ミ＿xノ
# 　　 　 /　　　 　 |       Feed me Stars ⭐ ️
# 　　　 /　 ヽ　　 ﾉ
# 　 　 │　　|　|　|
# 　／￣|　　 |　|　|
# 　| (￣ヽ＿_ヽ_)__)
# 　＼二つ
#
# Contributor Link, Thanks for your contribution:
# - https://github.com/Evil0ctal
# - https://github.com/Johnserf-Seed
#


from app.main import Host_IP, Host_Port
import uvicorn

if __name__ == '__main__':
    uvicorn.run('app.main:app', host=Host_IP, port=Host_Port, reload=True, log_level="info")

