import re
import struct
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

# 配置標準日誌系統
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("MortalDatEditor")

class TargetAttributes(BaseModel):
    """定義需要被優化的活俠傳關鍵屬性資料模型"""
    # --- 基礎貨幣與消耗性數值 ---
    money: Optional[int] = Field(None, alias="money", description="銀兩")
    mental: Optional[int] = Field(None, alias="mental", description="心相") 
    martial_point: Optional[int] = Field(None, alias="martial-point", description="武學點")
    contribution: Optional[int] = Field(None, alias="contribution", description="門派貢獻")
    fate: Optional[int] = Field(None, alias="fate", description="天命點")                             
    weapon_point: Optional[int] = Field(None, alias="weapon", description="打鐵點數")                  
    poison_point: Optional[int] = Field(None, alias="poison", description="煉毒點數")                  

    # --- 第一張圖：門派經營 ---
    assets: Optional[int] = Field(None, alias="assets", description="門派資產")                        
    fame: Optional[int] = Field(None, alias="fame", description="門派名聲")                            
    people: Optional[int] = Field(None, alias="people", description="門派人口")                        
    faction: Optional[int] = Field(None, alias="faction")                      
    team: Optional[int] = Field(None, alias="team", description="門派向心力")                             
    
    # --- 第二張圖：趙活核心屬性 ---
    life: Optional[int] = Field(None, alias="life", description="體力")                            
    dexterity: Optional[int] = Field(None, alias="dexterity", description="輕功") 
    stamina: Optional[int] = Field(None, alias="stamina", description="內力")                                      
    m_fist: Optional[int] = Field(None, alias="m-fist", description="拳掌")                        
    m_sword: Optional[int] = Field(None, alias="m-sword", description="刀劍")                      
    m_projectile: Optional[int] = Field(None, alias="m-projectile", description="暗器")            
    
    # --- 戰鬥與副職 ---
    combat_attack: Optional[int] = Field(None, alias="combat-attack-dice", description="爆發")
    combat_weapon_dice: Optional[int] = Field(None, alias="combat-weapon-dice", description="暗器爆發")     
    combat_defence: Optional[int] = Field(None, alias="combat-defence", description="防禦")        
    
    
    # --- 特質與抗性 ---
    literacy: Optional[int] = Field(None, alias="literacy", description="學問")                    
    talking: Optional[int] = Field(None, alias="talking", description="嘴力")                      
    poison_res: Optional[int] = Field(None, alias="poison-resistance", description="抗毒")         
    paralysis_res: Optional[int] = Field(None, alias="paralysis-resistance", description="抗麻")   
    behaviour: Optional[int] = Field(None, alias="behaviour", description="處世")                  
    karma: Optional[int] = Field(None, alias="karma", description="道德")
    disposition: Optional[int] = Field(None, alias="disposition", description="性情")  
    training: Optional[int] = Field(None, alias="training", description="修養")
    internal: Optional[int] = Field(None, alias="internal", description="陰陽")
       
    charisma: Optional[int] = Field(None, alias="charisma")    

    confucianism: Optional[int] = Field(None, alias="confucianism", description="儒學")            
    taoism: Optional[int] = Field(None, alias="taoism", description="道學")                        
    buddhism: Optional[int] = Field(None, alias="buddhism", description="佛學")                    


    # 解決 Pydantic V2 警告
    model_config = {"populate_by_name": True}


class DatSaveCipher:
    """Infra 層：純二進位檔案 I/O，絕對禁止將數據強制轉為字串"""
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def load_raw_bytes(self) -> bytes:
        if not self.file_path.exists():
            raise FileNotFoundError(f"找不到存檔檔案：{self.file_path}")
        logger.info("已成功讀取存檔二進位流。")
        return self.file_path.read_bytes()

    def save_raw_bytes(self, data: bytes) -> None:
        temp_file = self.file_path.with_suffix(".dat.tmp")
        try:
            temp_file.write_bytes(data)
            temp_file.replace(self.file_path)
            logger.info("二進位數據流已完美淨化並安全寫回磁碟。")
        except Exception as err:
            if temp_file.exists():
                temp_file.unlink()
            logger.error(f"寫入磁碟時發生異常: {str(err)}")
            raise err


class DatDataPurifierService:
    """Business Logic 層：在純 Bytes 環境下進行內存偏移量覆寫"""
    def __init__(self, cipher: DatSaveCipher):
        self.cipher = cipher

    def purge_stats(self, target_updates: TargetAttributes) -> None:
        raw_bytes = self.cipher.load_raw_bytes()
        update_map = target_updates.model_dump(by_alias=True, exclude_none=True)
        modified_count = 0

        for key_name, target_value in update_map.items():
            # 將屬性名稱轉為二進位
            key_bytes = key_name.encode('utf-8')
            # C# BinaryWriter 寫入字串時，前方會帶有一個字節的長度前綴
            length_prefix = bytes([len(key_bytes)])
            
            # 構建精準的二進位正則表達式：
            # 尋找：長度前綴 + 字串本身 + 緊跟在後的 4 個字節 (Int32)
            # 必須使用 re.DOTALL 確保 . 能夠匹配代表換行的 0x0A 字節
            pattern = re.escape(length_prefix + key_bytes) + b'(.{4})'
            
            # 將您要求的數值 (如 99999) 打包成 C# 格式的 4 Bytes 帶符號整數 (Little-Endian)
            new_value_bytes = struct.pack('<i', int(target_value))

            if re.search(pattern, raw_bytes, flags=re.DOTALL):
                # count=1 確保只替換該屬性的第一個實例，不污染其他同名欄位
                raw_bytes = re.sub(
                    pattern, 
                    length_prefix + key_bytes + new_value_bytes, 
                    raw_bytes, 
                    count=1, 
                    flags=re.DOTALL
                )
                logger.info(f"【二進位直寫成功】定位屬性 [{key_name}] -> 寫入小端序值: {target_value}")
                modified_count += 1

        if modified_count == 0:
            logger.warning("未能匹配任何二進位屬性，請確認原檔狀態。")
            return

        self.cipher.save_raw_bytes(raw_bytes)

def get_target_save_path() -> Path:
    """
    Entry(CLI) 層：處理使用者輸入並動態建構目標存檔路徑。
    嚴格遵循 Guard Clauses 減少巢狀，並僅使用 pathlib 處理路徑。
    """
    # 淨化 Hardcode：使用 Path.home() 動態解析當前使用者的家目錄
    # 註：將Steam ID (765**************) 替換成自己的 ID
    base_dir = Path.home() / "AppData" / "LocalLow" / "Obb Studio" / "Mortal" / "765**************"
    
    while True:
        try:
            user_input = input("請輸入欲修改的存檔編號 (001 - 020): ").strip()
            
            # Guard Clause 1: 確保輸入為純數字
            if not user_input.isdigit():
                logger.warning("輸入格式異常：請輸入純數字（例如 11 或 011）。")
                continue
                
            save_num = int(user_input)
            
            # Guard Clause 2: 邊界防禦，確保數值落在 1 到 20 之間
            if not (1 <= save_num <= 20):
                logger.warning("數值越界：存檔編號必須嚴格介於 1 至 20 之間。")
                continue
            
            # 將數字格式化為三位數字串 (如 011)
            file_name = f"Save_{save_num:03d}.dat"
            
            # 嚴格規範：僅能透過 pathlib 的 / 運算子組合路徑，絕對禁止字串相加 (+)
            target_path = base_dir / file_name
            
            return target_path
            
        except ValueError:
            logger.error("輸入解析失敗，請重新嘗試。")

def get_target_attributes() -> TargetAttributes:
    """
    Entry(CLI) 層：輪詢並提示使用者輸入各項屬性的數值。
    若使用者未輸入（直接按 Enter），則略過該屬性不進行修改。
    """
    logger.info("=== 屬性修改設定 ===")
    logger.info("接下來將逐一提示各項屬性。若不想修改該項，請直接按 Enter 跳過。")
    logger.info("====================")
    
    updates = {}
    
    # 運用 Pydantic 的反射機制，自動遍歷所有定義的屬性
    for key, field_info in TargetAttributes.model_fields.items():
        # 優先讀取 Field 中定義的 description (中文註釋)，若無則 fallback 至英文變數名稱
        display_name = field_info.description or key
        
        while True:
            # 程式主動提示屬性名稱，等待輸入
            user_input = input(f"請輸入 [{display_name}] 的目標數值 (直接按 Enter 跳過): ").strip()
            
            # Guard Clause 1: 若未輸入任何內容 (直接按 Enter)，立刻結束該屬性的詢問
            if not user_input:
                break
                
            try:
                # Guard Clause 2: 嚴格驗證並轉換為整數
                val = int(user_input)
                updates[key] = val
                logger.info(f"已記錄預定更新 -> {display_name} ({key}): {val}")
                # 成功記錄後跳出 while，繼續詢問下一個屬性
                break
            except ValueError:
                logger.warning(f"數值解析失敗：請為 [{display_name}] 輸入純數字，或直接按 Enter 跳過。")
                
    if not updates:
        logger.warning("您未設定任何屬性。若繼續執行，本次將不會有任何二進位數據被覆寫。")
        
    return TargetAttributes(**updates)

if __name__ == "__main__":
    try:
        # 使用原始字串 (r"...") 防禦 Windows 路徑轉義錯誤
        target_dat_path = get_target_save_path()
        logger.info(f"鎖定目標存檔路徑: {target_dat_path}")

        # 動態獲取使用者欲修改的屬性與數值
        mod_config = get_target_attributes()

        # 實例化 Infra 與 Business Logic 層
        cipher_layer = DatSaveCipher(file_path=target_dat_path)
        service_layer = DatDataPurifierService(cipher=cipher_layer)
        
        service_layer.purge_stats(target_updates=mod_config)

    except FileNotFoundError as fnf_err:
        logger.error(f"尋址失敗：未能在指定路徑找到該存檔。詳細資訊: {fnf_err}")
    except PermissionError as perm_err:
        logger.error(f"權限阻擋：無法讀寫該存檔檔案。詳細資訊: {perm_err}")
    except KeyboardInterrupt:
        logger.info("已接收到中斷指令，修改器程序安全終止。")
    
