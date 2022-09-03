import requests


r = requests.get("https://hypixel-app-api.senither.com/leaderboard/history?guild_id=5515e1ee0cf2978552888d31&perPage=9999999")
uuids = [
    "7b5558e9f0054c83824ce3d999880553",
    "bf8794f505124d7da30ae238a1efb4c2"
]

for player in r.json()["data"]:
    if player["uuid"].replace("-", "") in uuids:
        print(player)
