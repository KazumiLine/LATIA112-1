from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    TemplateSendMessage, ButtonsTemplate, PostbackAction,
    CarouselTemplate, CarouselColumn, URIAction,
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent,
    ButtonComponent, SeparatorComponent, SpacerComponent
)
import os
import json
from typing import List, Dict, Any

# Import the existing agent
from .agent import build_user_agent
from .models import get_engine, init_db

# LINE Bot configuration
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Initialize database
init_db()

class LineBotService:
    def __init__(self):
        self.user_agents = {}  # Cache for user agents
    
    def get_user_agent(self, user_id: str):
        """Get or create user agent for LINE user"""
        if user_id not in self.user_agents:
            self.user_agents[user_id] = build_user_agent(user_id)
        return self.user_agents[user_id]
    
    def handle_text_message(self, event: MessageEvent) -> TextSendMessage:
        """Handle text messages using LlamaIndex agent"""
        user_id = event.source.user_id
        user_input = event.text
        
        try:
            # Get user agent
            agent = self.get_user_agent(user_id)
            
            # Process with agent
            response = agent.chat(user_input)
            
            # Format response
            response_text = str(response)
            if len(response_text) > 2000:  # LINE message limit
                response_text = response_text[:1997] + "..."
            
            return TextSendMessage(text=response_text)
            
        except Exception as e:
            return TextSendMessage(text=f"抱歉，處理您的問題時發生錯誤：{str(e)}")
    
    def create_welcome_message(self) -> FlexSendMessage:
        """Create welcome message with quick actions"""
        bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="歡迎使用我們的智能客服！",
                        weight="bold",
                        size="lg",
                        color="#1DB446"
                    ),
                    SpacerComponent(size="sm"),
                    TextComponent(
                        text="我可以幫助您：",
                        size="sm",
                        color="#666666"
                    ),
                    SpacerComponent(size="sm"),
                    TextComponent(
                        text="• 查詢商品資訊\n• 查看訂單狀態\n• 了解購買流程\n• 售後服務諮詢\n• 下單購買商品",
                        size="sm",
                        color="#666666"
                    )
                ]
            ),
            footer=BoxComponent(
                layout="vertical",
                contents=[
                    ButtonComponent(
                        style="primary",
                        color="#1DB446",
                        action=PostbackAction(
                            label="查看商品",
                            data="action=view_products"
                        )
                    ),
                    SpacerComponent(size="sm"),
                    ButtonComponent(
                        style="secondary",
                        color="#666666",
                        action=PostbackAction(
                            label="購買流程",
                            data="action=purchase_guide"
                        )
                    ),
                    SpacerComponent(size="sm"),
                    ButtonComponent(
                        style="secondary",
                        color="#666666",
                        action=PostbackAction(
                            label="售後服務",
                            data="action=after_sales"
                        )
                    )
                ]
            )
        )
        
        return FlexSendMessage(alt_text="歡迎訊息", contents=bubble)
    
    def create_product_carousel(self, products: List[Dict]) -> CarouselTemplate:
        """Create product carousel for display"""
        columns = []
        
        for product in products[:10]:  # LINE carousel limit is 10
            column = CarouselColumn(
                title=product['name'][:40],  # LINE title limit
                text=product['outline'][:120] if product['outline'] else "無描述",  # LINE text limit
                actions=[
                    PostbackAction(
                        label="查看詳情",
                        data=f"action=product_detail&id={product['id']}"
                    ),
                    PostbackAction(
                        label="加入購物車",
                        data=f"action=add_to_cart&id={product['id']}"
                    )
                ]
            )
            columns.append(column)
        
        return CarouselTemplate(columns=columns)
    
    def create_quick_replies(self) -> List[TextSendMessage]:
        """Create quick reply options"""
        quick_replies = [
            TextSendMessage(
                text="我想查詢商品",
                quick_reply={
                    "items": [
                        {"type": "action", "action": {"type": "postback", "label": "電子產品", "data": "category=electronics"}},
                        {"type": "action", "action": {"type": "postback", "label": "服飾", "data": "category=clothing"}},
                        {"type": "action", "action": {"type": "postback", "label": "家居用品", "data": "category=home"}},
                        {"type": "action", "action": {"type": "postback", "label": "所有商品", "data": "category=all"}}
                    ]
                }
            ),
            TextSendMessage(
                text="我想了解購買流程",
                quick_reply={
                    "items": [
                        {"type": "action", "action": {"type": "postback", "label": "如何下單", "data": "guide=order"}},
                        {"type": "action", "action": {"type": "postback", "label": "付款方式", "data": "guide=payment"}},
                        {"type": "action", "action": {"type": "postback", "label": "配送說明", "data": "guide=delivery"}}
                    ]
                }
            ),
            TextSendMessage(
                text="我需要售後服務",
                quick_reply={
                    "items": [
                        {"type": "action", "action": {"type": "postback", "label": "退換貨", "data": "service=return"}},
                        {"type": "action", "action": {"type": "postback", "label": "維修保固", "data": "service=warranty"}},
                        {"type": "action", "action": {"type": "postback", "label": "客服聯絡", "data": "service=contact"}}
                    ]
                }
            )
        ]
        
        return quick_replies

# Create service instance
line_service = LineBotService()

# Webhook handler
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """Handle incoming messages"""
    
    # Handle specific commands
    if event.message.text.lower() in ['hi', 'hello', '你好', '您好']:
        welcome_msg = line_service.create_welcome_message()
        line_bot_api.reply_message(event.reply_token, welcome_msg)
        return
    
    if event.message.text.lower() in ['help', '幫助', '說明']:
        quick_replies = line_service.create_quick_replies()
        for msg in quick_replies:
            line_bot_api.reply_message(event.reply_token, msg)
        return
    
    # Process with LlamaIndex agent
    response = line_service.handle_text_message(event)
    line_bot_api.reply_message(event.reply_token, response)

@handler.add(MessageEvent, message=TextMessage)
def handle_postback(event):
    """Handle postback events"""
    try:
        data = event.postback.data
        
        if data.startswith("action="):
            action = data.split("=")[1]
            
            if action == "view_products":
                # Get products from database
                from .models import SessionLocal
                with SessionLocal() as session:
                    from .models import Product, ProductStatus
                    products = session.query(Product).filter_by(status=ProductStatus.NORMAL).limit(10).all()
                    
                    product_data = []
                    for p in products:
                        product_data.append({
                            'id': p.id,
                            'name': p.name,
                            'outline': p.outline or "無描述"
                        })
                
                if product_data:
                    carousel = line_service.create_product_carousel(product_data)
                    template_msg = TemplateSendMessage(alt_text="商品列表", template=carousel)
                    line_bot_api.reply_message(event.reply_token, template_msg)
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="目前沒有可用的商品"))
            
            elif action == "purchase_guide":
                guide_text = """📋 購買流程說明：

1️⃣ 瀏覽商品：選擇您喜歡的商品
2️⃣ 加入購物車：選擇規格和數量
3️⃣ 填寫資料：收貨人資訊和付款方式
4️⃣ 確認訂單：檢查訂單內容
5️⃣ 完成付款：選擇適合的付款方式
6️⃣ 等待發貨：我們會在24小時內發貨

有任何問題都可以詢問我！"""
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=guide_text))
            
            elif action == "after_sales":
                service_text = """🔧 售後服務說明：

📞 客服專線：0800-123-456
📧 客服信箱：service@example.com
⏰ 服務時間：週一至週日 9:00-21:00

🔄 退換貨政策：
• 七日鑑賞期（未拆封可退換）
• 一年保固（非人為損壞）
• 免費維修服務

需要協助請隨時聯繫我們！"""
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=service_text))
        
        elif data.startswith("category="):
            category = data.split("=")[1]
            # Handle category selection
            category_text = f"您選擇了 {category} 類別的商品。請告訴我您想了解哪個商品，或直接詢問具體問題！"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=category_text))
        
        elif data.startswith("guide="):
            guide_type = data.split("=")[1]
            # Handle specific guide requests
            if guide_type == "order":
                guide_text = "下單步驟：1.選擇商品 2.加入購物車 3.填寫資料 4.確認付款。需要我協助您下單嗎？"
            elif guide_type == "payment":
                guide_text = "支援付款方式：信用卡、銀行轉帳、貨到付款、電子錢包。您偏好哪種方式？"
            elif guide_type == "delivery":
                guide_text = "配送服務：標準配送3-5天，快速配送1-2天。滿500元免運費！"
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=guide_text))
        
        elif data.startswith("service="):
            service_type = data.split("=")[1]
            # Handle service requests
            if service_type == "return":
                service_text = "退換貨申請：請提供訂單編號和退貨原因，我們會安排取件。運費由買方負擔。"
            elif service_type == "warranty":
                service_text = "保固服務：電子產品1年保固，非人為損壞免費維修。需要維修請聯繫客服。"
            elif service_type == "contact":
                service_text = "客服聯絡：電話0800-123-456，信箱service@example.com，LINE@example_service"
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=service_text))
    
    except Exception as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"處理您的請求時發生錯誤：{str(e)}"))

def create_line_app():
    """Create Flask app for LINE Bot webhook"""
    app = Flask(__name__)
    
    @app.route("/callback", methods=['POST'])
    def callback():
        # Get X-Line-Signature header value
        signature = request.headers['X-Line-Signature']
        
        # Get request body as text
        body = request.get_data(as_text=True)
        app.logger.info("Request body: " + body)
        
        # Handle webhook body
        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)
        
        return 'OK'
    
    @app.route("/health")
    def health():
        return "LINE Bot is running!"
    
    return app

if __name__ == "__main__":
    # For testing LINE Bot locally
    app = create_line_app()
    app.run(debug=True, host='0.0.0.0', port=5001)