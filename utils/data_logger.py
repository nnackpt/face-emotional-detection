import csv
import os
import sqlite3
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import time

class DataLogger:
    def __init__(self, csv_path='emotion_logs.csv', db_path='data/emotion_logs.db'):
        """Initialize the data logger
        
        Args:
            csv_path (str): Path to the CSV file
            db_path (str): Path to the SQLite database
        """
        self.csv_path = csv_path
        self.db_path = db_path
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.csv_exists = os.path.exists(csv_path)
        if not self.csv_exists:
            with open(csv_path, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['timestamp', 'emotion', 'confidence', 'fps', 'eye_intensity', 'is_drowsy'])
        
        self._init_db()
        
    def _init_db(self):
        """สร้างฐานข้อมูล SQLite และตารางถ้ายังไม่มี"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS emotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            emotion TEXT NOT NULL,
            confidence REAL NOT NULL,
            fps REAL NOT NULL,
            eye_intensity REAL NOT NULL,
            is_drowsy INTEGER NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            happy_count INTEGER DEFAULT 0,
            sad_count INTEGER DEFAULT 0,
            angry_count INTEGER DEFAULT 0,
            surprised_count INTEGER DEFAULT 0,
            neutral_count INTEGER DEFAULT 0,
            drowsy_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            avg_fps REAL DEFAULT 0
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def log_emotion(self, emotion, confidence, fps, eye_intensity=0, is_drowsy=False):
        """บันทึกข้อมูลอารมณ์ลงใน CSV และ SQLite
        
        Args:
            emotion (str): อารมณ์ที่ตรวจจับได้
            confidence (float): ค่าความมั่นใจในการตรวจจับ (0-1)
            fps (float): อัตราเฟรมต่อวินาที
            eye_intensity (float): ความเข้มของบริเวณดวงตา (0-1)
            is_drowsy (bool): สถานะความง่วง
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.csv_path, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, emotion, confidence, fps, eye_intensity, 1 if is_drowsy else 0])
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO emotions (timestamp, emotion, confidence, fps, eye_intensity, is_drowsy) VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, emotion, confidence, fps, eye_intensity, 1 if is_drowsy else 0)
        )
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("SELECT id FROM daily_summary WHERE date = ?", (today,))
        result = cursor.fetchone()
        
        if result:
            cursor.execute(f"UPDATE daily_summary SET {emotion}_count = {emotion}_count + 1, total_count = total_count + 1 WHERE date = ?", (today,))
            
            if is_drowsy:
                cursor.execute("UPDATE daily_summary SET drowsy_count = drowsy_count + 1 WHERE date = ?", (today,))
                
            cursor.execute("SELECT total_count, avg_fps FROM daily_summary WHERE date = ?", (today,))
            total, avg_fps = cursor.fetchone()
            new_avg_fps = ((total - 1) * avg_fps + fps) / total
            cursor.execute("UPDATE daily_summary SET avg_fps = ? WHERE date = ?", (new_avg_fps, today))
            
        else:
            happy_count = 1 if emotion == 'happy' else 0
            sad_count = 1 if emotion == 'sad' else 0
            angry_count = 1 if emotion == 'angry' else 0
            surprised_count = 1 if emotion == 'surprised' else 0
            neutral_count = 1 if emotion == 'neutral' else 0
            drowsy_count = 1 if is_drowsy else 0
            
            cursor.execute(
                """INSERT INTO daily_summary 
                (date, happy_count, sad_count, angry_count, surprised_count, neutral_count, drowsy_count, total_count, avg_fps) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (today, happy_count, sad_count, angry_count, surprised_count, neutral_count, drowsy_count, 1, fps)
            )
        
        conn.commit()
        conn.close()
        
    def get_daily_summary(self, days=7):
        """ดึงข้อมูลสรุปรายวันย้อนหลัง
        
        Args:
            days (int): จำนวนวันย้อนหลังที่ต้องการดึงข้อมูล
            
        Returns:
            pd.DataFrame: ข้อมูลสรุปรายวัน
        """
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
        SELECT date, happy_count, sad_count, angry_count, surprised_count, neutral_count, drowsy_count, total_count, avg_fps
        FROM daily_summary
        ORDER BY date DESC
        LIMIT {days}
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
        
    def get_hourly_data(self, day=None):
        """ดึงข้อมูลรายชั่วโมงของวันที่กำหนด
        
        Args:
            day (str): วันที่ต้องการดึงข้อมูลในรูปแบบ YYYY-MM-DD หรือ None สำหรับวันนี้
            
        Returns:
            pd.DataFrame: ข้อมูลรายชั่วโมง
        """
        if day is None:
            day = datetime.datetime.now().strftime("%Y-%m-%d")
            
        conn = sqlite3.connect(self.db_path)
        
        query = f"""
        SELECT 
            strftime('%H', timestamp) as hour,
            emotion,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence,
            AVG(fps) as avg_fps,
            SUM(is_drowsy) as drowsy_count
        FROM emotions
        WHERE date(timestamp) = '{day}'
        GROUP BY hour, emotion
        ORDER BY hour, emotion
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
        
    def generate_daily_report(self, output_path='emotion_daily_report.html'):
        """สร้างรายงานสรุปรายวันในรูปแบบ HTML
        
        Args:
            output_path (str): ที่อยู่ไฟล์ HTML ที่จะสร้าง
            
        Returns:
            str: ที่อยู่ไฟล์ HTML ที่สร้าง
        """
        df_daily = self.get_daily_summary(days=7)
        
        if df_daily.empty:
            return None
            
        df_daily['date'] = pd.to_datetime(df_daily['date'])
        df_daily = df_daily.sort_values('date')
        
        plt.figure(figsize=(12, 8))
        
        emotions = ['happy_count', 'sad_count', 'angry_count', 'surprised_count', 'neutral_count']
        df_daily.plot(x='date', y=emotions, kind='bar', stacked=True, ax=plt.gca(),
                      color=['green', 'red', 'blue', 'purple', 'gray'])
                      
        plt.title('อารมณ์รายวัน (7 วันล่าสุด)')
        plt.xlabel('วันที่')
        plt.ylabel('จำนวนครั้ง')
        plt.legend(title='อารมณ์')
        
        chart_path = 'data/daily_emotions_chart.png'
        plt.savefig(chart_path)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>รายงานอารมณ์รายวัน</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .chart {{ margin: 20px 0; text-align: center; }}
                .chart img {{ max-width: 100%; }}
            </style>
        </head>
        <body>
            <h1>รายงานอารมณ์รายวัน</h1>
            <p>สร้างเมื่อ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>ตารางสรุปรายวัน (7 วันล่าสุด)</h2>
            <table>
                <tr>
                    <th>วันที่</th>
                    <th>มีความสุข</th>
                    <th>เศร้า</th>
                    <th>โกรธ</th>
                    <th>ประหลาดใจ</th>
                    <th>ปกติ</th>
                    <th>ง่วงนอน</th>
                    <th>จำนวนทั้งหมด</th>
                    <th>FPS เฉลี่ย</th>
                </tr>
        """
        
        for _, row in df_daily.iterrows():
            html_content += f"""
                <tr>
                    <td>{row['date'].strftime('%Y-%m-%d')}</td>
                    <td>{row['happy_count']}</td>
                    <td>{row['sad_count']}</td>
                    <td>{row['angry_count']}</td>
                    <td>{row['surprised_count']}</td>
                    <td>{row['neutral_count']}</td>
                    <td>{row['drowsy_count']}</td>
                    <td>{row['total_count']}</td>
                    <td>{row['avg_fps']:.2f}</td>
                </tr>
            """
            
        html_content += """
            </table>
            
            <div class="chart">
                <h2>กราฟแสดงอารมณ์รายวัน</h2>
                <img src="../data/daily_emotions_chart.png" alt="Daily Emotions Chart">
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return output_path
        
    def generate_hourly_report(self, day=None, output_path='emotion_hourly_report.html'):
        """สร้างรายงานสรุปรายชั่วโมงในรูปแบบ HTML
        
        Args:
            day (str): วันที่ต้องการสร้างรายงานในรูปแบบ YYYY-MM-DD หรือ None สำหรับวันนี้
            output_path (str): ที่อยู่ไฟล์ HTML ที่จะสร้าง
            
        Returns:
            str: ที่อยู่ไฟล์ HTML ที่สร้าง
        """
        if day is None:
            day = datetime.datetime.now().strftime("%Y-%m-%d")
            
        df_hourly = self.get_hourly_data(day)
        
        if df_hourly.empty:
            return None
            
        df_pivot = df_hourly.pivot(index='hour', columns='emotion', values='count').fillna(0)
        
        plt.figure(figsize=(14, 8))
        df_pivot.plot(kind='bar', stacked=True, ax=plt.gca(),
                      color=['blue', 'green', 'red', 'purple', 'gray'])
                      
        plt.title(f'อารมณ์รายชั่วโมง (วันที่ {day})')
        plt.xlabel('ชั่วโมง')
        plt.ylabel('จำนวนครั้ง')
        plt.legend(title='อารมณ์')
        
        chart_path = 'data/hourly_emotions_chart.png'
        plt.savefig(chart_path)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>รายงานอารมณ์รายชั่วโมง</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .chart {{ margin: 20px 0; text-align: center; }}
                .chart img {{ max-width: 100%; }}
            </style>
        </head>
        <body>
            <h1>รายงานอารมณ์รายชั่วโมง</h1>
            <p>วันที่: {day}</p>
            <p>สร้างเมื่อ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="chart">
                <h2>กราฟแสดงอารมณ์รายชั่วโมง</h2>
                <img src="../data/hourly_emotions_chart.png" alt="Hourly Emotions Chart">
            </div>
            
            <h2>ข้อมูลโดยละเอียด</h2>
            <table>
                <tr>
                    <th>ชั่วโมง</th>
                    <th>อารมณ์</th>
                    <th>จำนวนครั้ง</th>
                    <th>ความมั่นใจเฉลี่ย</th>
                    <th>FPS เฉลี่ย</th>
                </tr>
        """
        
        for _, row in df_hourly.iterrows():
            html_content += f"""
                <tr>
                    <td>{row['hour']}:00</td>
                    <td>{row['emotion']}</td>
                    <td>{row['count']}</td>
                    <td>{row['avg_confidence']:.2f}</td>
                    <td>{row['avg_fps']:.2f}</td>
                </tr>
            """
            
        html_content += """
            </table>
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return output_path