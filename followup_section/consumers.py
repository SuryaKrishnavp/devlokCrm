# from channels.generic.websocket import AsyncWebsocketConsumer
# from django.contrib.auth.models import AnonymousUser
# import json

# class FollowUpConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         user = self.scope.get("user")

#         # ✅ Import your model here to avoid AppRegistryNotReady errors
#         from auth_section.models import Sales_manager_reg

#         if user and not isinstance(user, AnonymousUser):
#             try:
#                 is_sales_manager = await Sales_manager_reg.objects.filter(user=user).aexists()
#                 if is_sales_manager:
#                     self.salesmanager_id = await Sales_manager_reg.objects.filter(user=user).values_list("id", flat=True).afirst()
#                     self.group_name = f"followups_notifications_{self.salesmanager_id}"

#                     await self.channel_layer.group_add(self.group_name, self.channel_name)
#                     await self.accept()
#                     print(f"✅ WebSocket Connected for Sales Manager ID: {self.salesmanager_id}")
#                     return
#             except Exception as e:
#                 print("❌ Exception during Sales Manager validation:", e)

#         await self.close()
#         print("❌ WebSocket Connection Rejected: Not a valid Sales Manager.")
