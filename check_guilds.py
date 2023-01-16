import requests

r = requests.get("https://api.guildleaderboard.com/leaderboard").json()
guild_ids = [i["id"] for i in r]

skykingsr = requests.get("https://skykings.net/lbdata").json()

for i in skykingsr:
    if i["guildid"] not in guild_ids:
        print(i["guildid"], i["name"], i["weight"])


"""
5f703f968ea8c99dcdd1967a Burning Circle 3946
60a198e18ea8c9bb7f6d90d2 Skykings Superior 3802.59
5fd433788ea8c9855c124950 Poshitos 3431.802
599791320cf25c25f39e85f4 Legion Of Super Evil 3286.192
"""