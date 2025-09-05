import hashlib
import discord
from discord import app_commands
from dotenv import load_dotenv
import os
import requests
import json
import random
from typing import Literal
import asyncio

load_dotenv()

token = os.getenv('TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
slash = app_commands.CommandTree(bot)

api = "https://thesieure.com/chargingws/v2"
id = os.getenv('TSR_PARTNER_ID')
key = os.getenv('TSR_PARTNER_KEY')

@bot.event
async def on_ready():
    print(f"Bot {bot.user} is ready!")
    try:
        synced = await slash.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Unable to sync commands: {e}")

@slash.command(name="ping", description="Lệnh dùng để kiểm tra độ trễ của bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"📶 | Độ trễ của bot là {round(bot.latency * 1000)}ms", ephemeral=True)

@slash.command(name="napthe", description="Lệnh dùng để nạp thẻ cào điện thoại")
@app_commands.describe(
    type="Loại thẻ (Viettel, Vinaphone)",
    mathe="Mã thẻ cào",
    seri="Số serial thẻ",
    value="Mệnh giá thẻ (Ví dụ: 10000, 20000,...)"
)
async def napthe(interaction: discord.Interaction, type: Literal['Viettel', 'Vinaphone'], mathe: str, seri: str, value: Literal['10000', '20000', '30000', '50000', '100000', '200000', '300000', '500000']):
    await interaction.response.defer(ephemeral=True)
    
    sign = str(hashlib.md5((key + mathe + seri).encode()).hexdigest())
    req_id = str(interaction.user.id + interaction.created_at.timestamp() + random.randint(11111, 99999))
    
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
            await interaction.followup.send("Thẻ đã được gửi và đang chờ xử lý. Bot sẽ thông báo kết quả qua DM khi hoàn tất.", ephemeral=True)
            await check_status(interaction, req_id, data)
        elif result["status"] == 1:
            await interaction.followup.send(f"Nạp thẻ thành công!", ephemeral=True)
        else:
            await interaction.followup.send(f"Lỗi: {result['message']}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Đã có lỗi xảy ra: {str(e)}", ephemeral=True)

async def check_status(interaction: discord.Interaction, req_id: str, data: dict):
    max_attempts = 10
    attempt = 0
    check_interval = 2
    
    check_data = {
        "partner_key": key,
        "request_id": req_id,
        "partner_id": id,
        "telco": data['telco'],
        "code": data['code'],
        "serial": data['serial'],
        "amount": data['amount'],
        "command": "check",
        "sign": str(hashlib.md5((key + data['code'] + data['serial']).encode()).hexdigest())
    }
    
    while attempt < max_attempts:
        try:
            r = requests.post(api, data=check_data)
            r_json = r.json()
            status = r_json['status']
            message = r_json.get('message', 'Không có thông báo')
            
            if status != 99:
                user = await bot.fetch_user(interaction.user.id)
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
                return
            
            attempt += 1
            await asyncio.sleep(check_interval)
        except Exception as e:
            print(f"Error when checking request {req_id}: {e}")
            user = await bot.fetch_user(interaction.user.id)
            await user.send(f"Đã có lỗi xảy ra khi kiểm tra trạng thái thẻ: {str(e)}")
            await interaction.followup.send(f"Đã có lỗi xảy ra khi kiểm tra trạng thái: {str(e)}", ephemeral=True)
            return
        

    user = await bot.fetch_user(interaction.user.id)
    await user.send(f"Không thể kiểm tra trạng thái thẻ của bạn (request_id: {req_id}). Vui lòng liên hệ hỗ trợ.")
    await interaction.followup.send(f"Không thể kiểm tra trạng thái thẻ sau {max_attempts} lần thử. Vui lòng thử lại sau.", ephemeral=True)

if __name__ == "__main__":
    bot.run(token)