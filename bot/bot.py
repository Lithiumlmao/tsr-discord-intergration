import hashlib
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv
import os
import requests
import json
from typing import Literal

load_dotenv()

token = os.getenv('TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
slash = app_commands.CommandTree(bot)

api = "https://thesieure.com/chargingws/v2"

id = os.getenv('TSR_PARTNER_ID')
key = os.getenv('TSR_PARTNER_KEY')

pending_requests = {}

@bot.event
async def on_ready():
    print(f"Bot {bot.user} is ready!")
    try:
        synced = await slash.sync()
        print(f"Synced {len(synced)} command(s).")
        check_pending.start()
    except Exception as e:
        print(f"Unable to sync commands: {e}")

@slash.command(name="napthe", description="Lệnh dùng để nạp thẻ cào điện thoại")
@app_commands.describe(
    type="Loại thẻ (Viettel, Vinaphone)",
    mathe="Mã thẻ cào",
    seri="Số serial thẻ",
    value="Mệnh giá thẻ (Ví dụ: 10000, 20000,...)"
)
async def napthe(interaction: discord.Interaction, type: Literal['Viettel', 'Vinaphone'], mathe: str, seri: str, value: Literal['10000', '20000', '30000', '50000', '100000', '200000', '300000', '500000']):
    await interaction.response.defer()
    
    sign = str(hashlib.sha256((key + mathe + seri).encode()).hexdigest())
    
    req_id = int(interaction.user.id + interaction.created_at.timestamp())
    
    data = {
        "sign": sign,
        "partner_id": id,
        "partner_key": key,
        "telco": type.upper(),
        "code": mathe,
        "serial": seri,
        "amount": value,
        "request_id": req_id,
        "command": "charging"
    }
    try:
        response = requests.post(api, data=data)
        result = response.json()
        if result["status"] == 99:
            await interaction.followup.send("Thẻ đã được gửi và đang chờ xử lý. Sẽ gửi DM khi hoàn thành.", ephemeral=True)
            pending_requests[req_id] = {
                'user_id': interaction.user.id,
                'telco': data['telco'],
                'code': data['code'],
                'serial': data['serial'],
                'amount': data['amount']
            }
        elif result["status"] == 1:
            await interaction.followup.send(f"Nạp thẻ thành công!",ephemeral=True)
        else:
            await interaction.followup.send(f"Lỗi: {result['message']}",ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Đã có lỗi xảy ra: {str(e)}",ephemeral=True)

@tasks.loop(seconds=30)
async def check_pending():
    for req_id, data in list(pending_requests.items()):
        check_data = {
            "telco": data['telco'],
            "code": data['code'],
            "serial": data['serial'],
            "amount": data['amount'],
            "command": "check",
            "sign": str(hashlib.sha256((key + data['code'] + data['serial']).encode()).hexdigest())
        }
        try:
            r = requests.get(api, data=check_data)
            r_json = r.json()
            status = r_json['status']
            message = r_json.get('message', 'Không có thông báo')
            
            if status != 99:
                user = await bot.fetch_user(data['user_id'])
                match status:
                    case 1:
                        await user.send(f"Thẻ của bạn đã nạp thành công! Thông báo: {message}")
                    case 2:
                        await user.send(f"Thẻ sai mệnh giá. Thông báo: {message}")
                    case 3:
                        await user.send(f"Thẻ lỗi hoặc đã sử dụng. Thông báo: {message}")
                    case 4:
                        await user.send(f"Hệ thống bảo trì hoặc lỗi mạng. Thông báo: {message}")
                    case _:
                        await user.send(f"Nạp thẻ không thành công. Mã lỗi: {status}. Thông báo: {message}")
                del pending_requests[req_id]
        except Exception as e:
            print(f"Error when checking request {req_id}: {e}")

@check_pending.before_loop
async def before_check_pending():
    await bot.wait_until_ready()

if __name__ == "__main__":
    bot.run(token)
