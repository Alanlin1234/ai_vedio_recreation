#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新抖音爬虫Cookie
"""

import requests
import json

# 用户提供的抖音Cookie
DOUYIN_COOKIE = "enter_pc_once=1; UIFID_TEMP=1ee16134db40129a5ff28e6a352dddaa8524f48fc5e4ea6d697d6a182d7836e4c531d3c842a99eccfcdefba8251836e427fb651a058c5869bdb5b61d634532721b5b7d09e2f7545b7c01265e63217665; s_v_web_id=verify_mj1ghhlf_VdnUf6EH_C5EP_4sHW_AkZr_F7w8MzYXGWHW; volume_info=%7B%22isMute%22%3Atrue%2C%22isUserMute%22%3Atrue%2C%22volume%22%3A0.5%7D; dy_swidth=1707; dy_sheight=1067; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1707%2C%5C%22screen_height%5C%22%3A1067%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A32%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; hevc_supported=true; passport_csrf_token=243d412dfe554d795d701cb2b78c7125; passport_csrf_token_default=243d412dfe554d795d701cb2b78c7125; fpk1=U2FsdGVkX18v/RrulbnNjBkVuNmBfLzZFw+6RX44RN50d9shgSsx0/uE+2SRODWSqq0HtMsh8Qr9rqAi2jfVrg==; fpk2=e8db1a910ee088b469ecfd2b6a9b9da5; record_force_login=%7B%22timestamp%22%3A1765458634202%2C%22force_login_video%22%3A1%2C%22force_login_live%22%3A0%2C%22force_login_direct_video%22%3A0%7D; bd_ticket_guard_client_web_domain=2; is_dash_user=1; UIFID=1ee16134db40129a5ff28e6a352dddaa8524f48fc5e4ea6d697d6a182d7836e4c531d3c842a99eccfcdefba8251836e444445b3bfc21e2b85724354141fa091bc50f5dad359701dd87baad5cc45e4933158cb05b93d6a3c54c8791a606f14ef11c30c2a4545aa66504e04b2ddaa0a3d626811d574f8d4ddf2330efa334f8c48dc43ea9d0f2d3984ba3be4bd3f720b86e969e6f3a0870cf4562ad2a045dce5f67; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A1%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; passport_mfa_token=CjdEZoeC3fcnQjQbuNKaD6T946WTfLPdyv1%2FBc%2F7WpNaFIOdq9mlEhosFpiLYKBeALw8%2F6%2BFJznqGkoKPAAAAAAAAAAAAABP0YN%2Fr1jS3mXcWCnNztgI8%2F7yO3z9j09BUrLL8ngON%2Bhus4SCs%2BG7G%2Bye%2BRRnpwA69hC684MOGPax0WwgAiIBAxNv5QM%3D; d_ticket=5ab544c701f4866eac57c57b13ea845c46c88; passport_assist_user=CkE1Sj4TVs5Rb_hPKGiN8j8WKvkJzS_gsPxyMUnxKueeS2JY3M9PySFMX-exqOFdH6gvLRBH4lrSIYr9uFQ74aRcvBpKCjwAAAAAAAAAAAAAT9FIdeO9XuR4nfdpC1eZjIiz73bq599nNS4HrJ6eCUks12tNu9iD1xPnZR-QDlhwDUMQp_ODDhiJr9ZUIAEiAQPKxd02; n_mh=SLdp6upM6PCVcwQbF4IKorila1Ad48nOrgAeJZ9OyRc; sid_guard=aab909bd0d8deca5aa7ff7411e67ce9a%7C1765459094%7C5184000%7CMon%2C+09-Feb-2026+13%3A18%3A14+GMT; uid_tt=4fc69f69233491d3cab18360c59a6f27; uid_tt_ss=4fc69f69233491d3cab18360c59a6f27; sid_tt=aab909bd0d8deca5aa7ff7411e67ce9a; sessionid=aab909bd0d8deca5aa7ff7411e67ce9a; sessionid_ss=aab909bd0d8deca5aa7ff7411e67ce9a; session_tlb_tag=sttt%7C6%7CqrkJvQ2N7KWqf_dBHmfOmv_________YJbTIk7bKPxPUVqhzzaV5YZb5TSP1T72LfhHbMEs0Glc%3D; session_tlb_tag_bk=sttt%7C6%7CqrkJvQ2N7KWqf_dBHmfOmv_________YJbTIk7bKPxPUVqhzzaV5YZb5TSP1T72LfhHbMEs0Glc%3D; is_staff_user=false; sid_ucp_v1=1.0.0-KDYzODMzYjNjMDVlNjkzMDRkZGFiMmQ1MTllYjI1NzI3NGZhZTAwYzgKIQiZ1MDg8syNBBCWievJBhjvMSAMMPKDy7MGOAdA9AdIBBoCbGYiIGFhYjkwOWJkMGQ4ZGVjYTVhYTdmZjc0MTFlNjdjZTlh; ssid_ucp_v1=1.0.0-KDYzODMzYjNjMDVlNjkzMDRkZGFiMmQ1MTllYjI1NzI3NGZhZTAwYzgKIQiZ1MDg8syNBBCWievJBhjvMSAMMPKDy7MGOAdA9AdIBBoCbGYiIGFhYjkwOWJkMGQ4ZGVjYTVhYTdmZjc0MTFlNjdjZTlh; _bd_ticket_crypt_cookie=e37986cbef4517d95591fb80b19656d9; __security_server_data_status=1; login_time=1765459092332; publish_badge_show_info=%220%2C0%2C0%2C1765459092914%22; DiscoverFeedExposedAd=%7B%7D; SelfTabRedDotControl=%5B%7B%22id%22%3A%227580205461530478626%22%2C%22u%22%3A3%2C%22c%22%3A0%7D%5D; __ac_nonce=0693b7b8c00c819082890; __ac_signature=_02B4Z6wo00f01uhLkXwAAIDDdrQPeLwOshLoa5XAANM26b; douyin.com; device_web_cpu_core=32; device_web_memory_size=8; architecture=amd64; IsDouyinActive=true; strategyABtestKey=%221765505932.881%22; ttwid=1%7C6hVfeJStTSDR1Hr4uqiJwuVrHIl2jlOZH3GC8FEXKug%7C1765505936%7C66f06b5977295b85e8d8016cb4db5d06174afbc91d38550f495c85f6fb5e22cd; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCSDJrZkgrUVBDcWwvUnBBeGx4T1lzRFNUa2VNZTM4ZUV1dkw1b2VCNTVaZnFRK3BaOGV4Rkt3cDIzSElRZEVCR3IwcDlNMzh4WmFvOHNEMkJMem42QTQ9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; home_can_add_dy_2_desktop=%221%22; biz_trace_id=ef797cc1; odin_tt=7e26980d01f0c12fcc41bda603f3d4b3b01d73068958789e01274ef7635594047372256888963902e90bfefad8db19c97a5c4c8fb94838f9cf1f810dec04dfb30920a16d3f385a62a062d5b93203fcf1; gulu_source_res=eyJwX2luIjoiNmRhNjZlNzVjY2QxODk5ZDMwZmMzZGQzN2I4ZmM2MWQxZjQ1ZDNmYWFmYzU4OTQxOWViNzViZjA1ZTEyZmEzMiJ9; __security_mc_1_s_sdk_crypt_sdk=0e1026f8-41b9-9029; __security_mc_1_s_sdk_cert_key=051e5408-4abd-a043; __security_mc_1_s_sdk_sign_data_key_web_protect=a72f7fa6-44ed-b15b; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJIMmtmSCtRUENxbC9ScEF4bHhPWXNEU1RrZU1lMzhlRXV2TDVvZUI1NVpmcVErcFo4ZXhGS3dwMjNISVFkRUJHcjBwOU0zOHhaYW84c0QyQkx6bjZBND0iLCJ0c19zaWduIjoidHMuMi42MGQxZGRkZGU3MDgxMjRkMTgyMTJmNGY0OTY5ZTQxMTNhYjk5YjY3YTIzMTY0OGFkODNiMGJmNzU0ZGFhNWUzYzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsInJlcV9jb250ZW50Ijoic2VjX3RzIiwicmVxX3NpZ24iOiJYZi9PT1A2cDRrVEJ2VENDTytxdFd0b21UNUhKd0RHMCtST3E3bmJacTM4PSIsInNlY190cyI6IiM3OXptNEExbldIbkNSaXB5ZU05WS94UXhVcWdETDBDNkIxSjducWpPZ2c2QytiK1hPMDJMQTB5anQzcUQifQ%3D%3D; download_guide=%223%2F20251212%2F0%22; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f27313135353d3433353030333234272927676c715a75776a716a666a69273f2763646976602778; bit_env=bg9Ok_x4ywckTbtazDyh0t4YM6hKzQ9s9-UsaYJzQbLIYAaeHgLaI1I1_Fs1jArTV43DGyarMj3cNx__QwBxp_pdHrOBZt_rzaIVpHeCApn4vnF5YAoRFk4FBjXBYfU4LRYTtiF3IFvbZWRNGh_BihT61xEoLj1Wc3ap6m4I_LQ0ar3jlc0FSACNlXmO-KwLLCaeKkK_euiEtcM-Yqmw1aJdMGq2mp3oKADwZpBIYYrckY2eN4goSM71S6NT2INZV5of-M-CUgKBkPkYtWuMGOMLhICdZD3xzmqa4ttkZ3RADLounp1XsGgqOEWOgQ6pPgtEAydVV1V3F0fH_X3VPEFHTpMpIHKd6Jy_YtiD0mwit8bTof_kGf2_wadqf0tcGi8PbO62OX357aJbsOLddzcHqP64-pSUHtV0QwgrdjjmH88BE5FmDbIMnEn0S-867meTOMnV9GaESEZBwpOWUu04QLJJ6e69cotrCmuJ1nT4yYW8wGcz9KpMKe0AEZgi"

# 爬虫API地址
CRAWLER_API_URL = "http://localhost:8081/api/hybrid"

# 更新抖音Cookie
print(f"开始更新抖音Cookie...")
try:
    response = requests.post(
        f"{CRAWLER_API_URL}/update_cookie",
        json={
            "service": "douyin",
            "cookie": DOUYIN_COOKIE
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Cookie更新成功: {result.get('data', {}).get('message', '')}")
    else:
        print(f"✗ Cookie更新失败，状态码: {response.status_code}")
        print(f"  响应内容: {response.text}")
except Exception as e:
    print(f"✗ Cookie更新失败: {str(e)}")
    import traceback
    print(f"  异常堆栈: {traceback.format_exc()}")
