from django.shortcuts import render
from rest_framework.decorators import api_view,permission_classes
from auth_section.permissions import IsSalesManagerUser,IsCustomAdminUser
from auth_section.models import Sales_manager_reg
from leads_section.models import Leads
from rest_framework.response import Response
from .serializers import DatabankSerializer,DataBankEditSerializer,DataBankGETSerializer,DataBankImageSerializer
from rest_framework import status
from .models import DataBank,DataBankImage
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from django.db.models import Q
from django.http import JsonResponse
from .filters import DataBankFilter
from django.core.mail import send_mail
from django.conf import settings
from auth_section.models import Ground_level_managers_reg
from rest_framework.permissions import IsAuthenticated
from project_section.models import Project_db
from django.core.mail import EmailMessage
from django.conf import settings
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from leads_section.models import Leads
import os





@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def get_lead_data(request, lead_id):
    user = request.user
    sales_manager = Sales_manager_reg.objects.filter(user=user.id).first()

    if not sales_manager:
        return Response({"error": "Sales Manager not found"}, status=status.HTTP_404_NOT_FOUND)


    # Get Lead
    lead = get_object_or_404(Leads, id=lead_id)

    # Prepare response
    lead_data = {
        "name": lead.name,
        "email": lead.email,
        "phonenumber": lead.phonenumber,
        "district": lead.district,
        "place": lead.place,
        "address":lead.address,
        "purpose": lead.purpose,
        "mode_of_purpose":lead.mode_of_purpose,
        "follower": lead.follower
    }
    return Response(lead_data, status=status.HTTP_200_OK)


        
    
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSalesManagerUser])
def store_data_into_db(request, lead_id):
    user = request.user
    sales_manager = Sales_manager_reg.objects.filter(user=user.id).first()

    if not sales_manager:
        return Response({"error": "Sales Manager not found"}, status=status.HTTP_404_NOT_FOUND)

    lead = get_object_or_404(Leads, id=lead_id)
    if lead.staff_id != sales_manager.id:
        return Response({"error": "Sales Manager mismatch"}, status=status.HTTP_403_FORBIDDEN)

    print("Incoming data:", request.data)  # ✅ Print full data
    serializer = DatabankSerializer(data=request.data)

    if serializer.is_valid():
        databank_entry = DataBank.objects.create(
            lead=lead,
            follower=sales_manager,
            timestamp=timezone.now(),
            **serializer.validated_data
        )
        return Response({"success": "Data stored successfully", "id": databank_entry.id}, status=status.HTTP_201_CREATED)

    print("Validation errors:", serializer.errors)  # ✅ Show why it failed
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['PATCH'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])  
def update_databank(request, databank_id):
    staff = request.user

    # Ensure the authenticated user is a Sales Manager
    if not hasattr(staff, 'sales_manager_reg'):
        return Response({"error": "Not a valid sales manager"}, status=403)
    
    salesmanger = Sales_manager_reg.objects.filter(user = staff.id).first()

    try:
        databank = DataBank.objects.get(id=databank_id)
    except DataBank.DoesNotExist:
        return Response({"error": "DataBank entry not found"}, status=404)

    # Check if the logged-in staff is the follower of this databank entry
    if databank.follower_id != salesmanger.id:
        return Response({'message': 'Data editable only by the assigned follower'}, status=403)

    # Partially update only provided fields
    serializer = DataBankEditSerializer(databank, data=request.data, partial=True)
    if serializer.is_valid():
        print(serializer.errors)
        serializer.save()
        return Response(serializer.data, status=200)
    
    return Response(serializer.errors, status=400)





@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def view_databank_data(request):
    staff = request.user

    # Ensure the authenticated user is a Sales Manager
    if not hasattr(staff, 'sales_manager_reg'):
        return Response({"error": "Not a valid sales manager"}, status=403)
    
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()

    data = DataBank.objects.filter(follower_id=salesmanager.id)
    
    serializer = DataBankEditSerializer(data, many=True)
    return Response(serializer.data, status=200)




@api_view(['DELETE'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])  
def delete_databank(request, databank_id):
    staff = request.user

    # Ensure the authenticated user is a Sales Manager
    if not hasattr(staff, 'sales_manager_reg'):
        return Response({"error": "Not a valid sales manager"}, status=403)
    
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    try:
        databank = DataBank.objects.get(id=databank_id)
    except DataBank.DoesNotExist:
        return Response({"error": "DataBank entry not found"}, status=404)

    if databank.follower_id != salesmanager.id:
        return Response({"error": "Only the assigned follower can delete this entry"}, status=403)

    databank.delete()
    return Response({"message": "DataBank entry deleted successfully"}, status=200)





from leads_section.serializers import LeadsViewSerializer
from project_section.serializers import ProjectSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def search_databank(request):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)
    query = request.GET.get('q', '').strip()

    if not query:
        return JsonResponse({"error": "Query parameter is required"}, status=400)

    # 1️⃣ Search in Databank
    databank_results = DataBank.objects.filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(phonenumber__icontains=query) |
        Q(district__icontains=query) |
        Q(place__icontains=query) |
        Q(purpose__icontains=query) |
        Q(mode_of_property__icontains=query) |
        Q(demand_price__icontains=query) |
        Q(location_proposal_district__icontains=query) |
        Q(location_proposal_place__icontains=query) |
        Q(area_in_sqft__icontains=query) |
        Q(building_roof__icontains=query) |
        Q(number_of_floors__icontains=query) |
        Q(building_bhk__icontains=query) |
        Q(projects__project_name__icontains=query) |
        Q(projects__importance__icontains=query)
    )

    if databank_results.exists():
        return JsonResponse({
            "source": "databank",
            "results": DataBankGETSerializer(databank_results, many=True).data
        })

    # 2️⃣ If no Databank results, search in Leads
    lead_results = Leads.objects.filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(phonenumber__icontains=query) |
        Q(district__icontains=query) |
        Q(place__icontains=query) |
        Q(purpose__icontains=query) |
        Q(mode_of_purpose__icontains=query) |
        Q(message__icontains=query) |
        Q(status__icontains=query) |
        Q(stage__icontains=query) |
        Q(follower__icontains=query)
    )

    if lead_results.exists():
        return JsonResponse({
            "source": "leads",
            "results": LeadsViewSerializer(lead_results, many=True).data
        })

    # 3️⃣ If no Leads results, search in Projects
    project_results = Project_db.objects.filter(
        Q(project_name__icontains=query) |
        Q(importance__icontains=query) |
        Q(description__icontains=query)
    )

    if project_results.exists():
        return JsonResponse({
            "source": "projects",
            "results": ProjectSerializer(project_results, many=True).data
        })

    # 4️⃣ If no matches found in any, return empty response
    return JsonResponse({"source": "none", "results": []})








@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def salesmanager_search_databank(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return JsonResponse({"error": "Query parameter is required"}, status=400)
    staff = request.user

    # Check if the user is a sales manager
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    if not salesmanager:
        return Response({"error": "Not a valid sales manager"}, status=status.HTTP_403_FORBIDDEN)

    # 1️⃣ Search in Databank
    databank_results = DataBank.objects.filter(
        (Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(phonenumber__icontains=query) |
        Q(district__icontains=query) |
        Q(place__icontains=query) |
        Q(purpose__icontains=query) |
        Q(mode_of_property__icontains=query) |
        Q(demand_price__icontains=query) |
        Q(location_proposal_district__icontains=query) |
        Q(location_proposal_place__icontains=query) |
        Q(area_in_sqft__icontains=query) |
        Q(building_roof__icontains=query) |
        Q(number_of_floors__icontains=query) |
        Q(building_bhk__icontains=query) |
        Q(projects__project_name__icontains=query) |
        Q(projects__importance__icontains=query))&
        Q(follower=salesmanager)
    )

    if databank_results.exists():
        return JsonResponse({
            "source": "databank",
            "results": DataBankGETSerializer(databank_results, many=True).data
        })

    # 2️⃣ If no Databank results, search in Leads
    lead_results = Leads.objects.filter(
        (Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(phonenumber__icontains=query) |
        Q(district__icontains=query) |
        Q(place__icontains=query) |
        Q(purpose__icontains=query) |
        Q(mode_of_purpose__icontains=query) |
        Q(message__icontains=query) |
        Q(status__icontains=query) |
        Q(stage__icontains=query) |
        Q(follower__icontains=query))&
        Q(staff_id=salesmanager.id)
    )

    if lead_results.exists():
        return JsonResponse({
            "source": "leads",
            "results": LeadsViewSerializer(lead_results, many=True).data
        })

    # 3️⃣ If no Leads results, search in Projects
    project_results = Project_db.objects.filter(
        (Q(project_name__icontains=query) |
        Q(importance__icontains=query) |
        Q(description__icontains=query)) &
        Q(data_bank__follower=salesmanager)
    )

    if project_results.exists():
        return JsonResponse({
            "source": "projects",
            "results": ProjectSerializer(project_results, many=True).data
        })

    # 4️⃣ If no matches found in any, return empty response
    return JsonResponse({"source": "none", "results": []})




@api_view(['GET'])
@permission_classes([AllowAny])
def filter_data_banks(request):
    
    # Apply filters
    filtered_data = DataBankFilter(request.GET, queryset=DataBank.objects.all()).qs
    
    # Serialize filtered results
    serializer = DataBankGETSerializer(filtered_data, many=True)
    
    return Response(serializer.data, status=status.HTTP_200_OK)













@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_matching_pdf(request, property_id):
    try:
        new_property = get_object_or_404(DataBank, id=property_id)

        # Define opposite purpose for matching
        opposite_purpose_map = {
            "For Selling a Property": "For Buying a Property",
            "For Buying a Property": "For Selling a Property",
            "For Rental or Lease": "Looking to rent or Lease a Property",
            "Looking to rent or Lease Property": "For Rental or Lease",
        }
        opposite_purpose = opposite_purpose_map.get(new_property.purpose, None)

        # Get potential matches
        potential_matches = DataBank.objects.filter(
            purpose=opposite_purpose,
            mode_of_property=new_property.mode_of_property,
        )

        # Relaxed Matching for Broader Results
        if not potential_matches.exists():
            potential_matches = DataBank.objects.filter(
                purpose=opposite_purpose,
                mode_of_property__in=["other", new_property.mode_of_property],
            )

        # Ranking Logic for Best Matches
        ranked_matches = []
        for match in potential_matches:
            score = 0

            if match.mode_of_property == new_property.mode_of_property:
                score += 4

            # Location Matching
            if new_property.purpose in ["buy", "rental seeker"]:
                if match.district == new_property.location_proposal_district:
                    score += 3
                if (
                    match.place and new_property.location_proposal_place and
                    match.place.lower() == new_property.location_proposal_place.lower()
                ):
                    score += 2
            else:
                if match.location_proposal_district == new_property.district:
                    score += 3
                if (
                    match.location_proposal_place and new_property.place and
                    match.location_proposal_place.lower() == new_property.place.lower()
                ):
                    score += 2

            # Price Range (±10%)
            if match.demand_price and new_property.demand_price:
                if match.demand_price * 0.9 <= new_property.demand_price <= match.demand_price * 1.1:
                    score += 5

            # Area, Floors, BHK, Roof
            if match.area_in_sqft == new_property.area_in_sqft:
                score += 2
            if match.building_bhk == new_property.building_bhk:
                score += 2
            if match.number_of_floors == new_property.number_of_floors:
                score += 1
            if match.building_roof == new_property.building_roof:
                score += 1

            if score > 0:
                ranked_matches.append((score, match))

        # Sort by score descending
        ranked_matches.sort(reverse=True, key=lambda x: x[0])

        if not ranked_matches:
            ground_staff_emails = Ground_level_managers_reg.objects.values_list("email", flat=True)
            if ground_staff_emails:
                subject = "⚠️ No Matches Found for New Property"
                message = (
                    f"A new property (ID: {new_property.id}, Purpose: {new_property.purpose}, Type: {new_property.mode_of_property}) "
                    f"has been added, but no matching properties were found."
                )
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, list(ground_staff_emails), fail_silently=True)

            return Response(
                {"message": "⚠️ No matching properties found! Email notification sent to Ground-Level Staff."},
                status=status.HTTP_200_OK,
            )

        # === PDF Generation ===
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50

        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(100, y, "Top Matching Properties")
        y -= 30

        for score, match in ranked_matches[:5]:  # Top 5 matches
            if y < 200:
                pdf.showPage()
                y = height - 50

            pdf.setFont("Helvetica", 10)
            pdf.drawString(50, y, f"District: {match.district} | Place: {match.place} | Price: ₹{match.demand_price} | Area: {match.area_in_sqft} sqft | BHK: {match.building_bhk or 'N/A'} | Roof: {match.building_roof or 'N/A'}")
            y -= 20

            images = match.images.all()
            for image_obj in images:
                image_path = image_obj.image.path
                if os.path.exists(image_path):
                    try:
                        img = ImageReader(image_path)
                        if y < 170:
                            pdf.showPage()
                            y = height - 50
                        pdf.drawImage(img, 50, y - 120, width=200, height=120, preserveAspectRatio=True)
                        y -= 140
                    except Exception:
                        y -= 10

        pdf.save()
        buffer.seek(0)

        # === Email with PDF attachment ===
        subject = f"Matching Properties PDF for Property ID {property_id}"
        body = "Hello,\n\nPlease find the attached PDF with top matching properties."
        to_email = new_property.email

        if not to_email:
            return Response({"error": "Client email not found."}, status=400)

        email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])
        email.attach(f"matching_properties_{property_id}.pdf", buffer.read(), "application/pdf")
        email.send(fail_silently=False)

        return Response({"message": "Matching properties PDF sent to client successfully."})

    except Exception as e:
        return Response({"error": str(e)}, status=500)










@api_view(['GET'])
@permission_classes([AllowAny])
def match_property(request, property_id):
    try:
        new_property = get_object_or_404(DataBank, id=property_id)

        # Define opposite purpose for matching
        opposite_purpose_map = {
            "For Selling a Property": "For Buying a Property",
            "For Buying a Property": "For Selling a Property",
            "For Rental or Lease": "Looking to rent or Lease a Property",
            "Looking to rent or Lease Property": "For Rental or Lease",
        }
        opposite_purpose = opposite_purpose_map.get(new_property.purpose, None)

        # Get potential matches
        potential_matches = DataBank.objects.filter(
            purpose=opposite_purpose,
            mode_of_property=new_property.mode_of_property,
        )

        # Relaxed Matching for Broader Results
        if not potential_matches.exists():
            potential_matches = DataBank.objects.filter(
                purpose=opposite_purpose,
                mode_of_property__in=["other", new_property.mode_of_property],
            )

        # Ranking Logic for Best Matches
        ranked_matches = []
        for match in potential_matches:
            score = 0

            # Strong Matches - Property Type
            if match.mode_of_property == new_property.mode_of_property:
                score += 4

            # Location Matching Logic (District & Place)
            if new_property.purpose in ["buy", "rental seeker"]:
                if match.district == new_property.location_proposal_district:
                    score += 3
                if (
                    match.place
                    and new_property.location_proposal_place
                    and match.place.lower() == new_property.location_proposal_place.lower()
                ):
                    score += 2
            else:
                if match.location_proposal_district == new_property.district:
                    score += 3
                if (
                    match.location_proposal_place
                    and new_property.place
                    and match.location_proposal_place.lower() == new_property.place.lower()
                ):
                    score += 2

            # Price Range (±10% Flexibility)
            if match.demand_price and new_property.demand_price:
                if match.demand_price * 0.9 <= new_property.demand_price <= match.demand_price * 1.1:
                    score += 5

            # Area, Floors, and BHK Matching
            if match.area_in_sqft == new_property.area_in_sqft:
                score += 2
            if match.building_bhk and new_property.building_bhk and match.building_bhk == new_property.building_bhk:
                score += 2
            if match.number_of_floors and new_property.number_of_floors and match.number_of_floors == new_property.number_of_floors:
                score += 1

            # Building Roof Check
            if match.building_roof == new_property.building_roof:
                score += 1

            # Append valid matches with score
            if score > 0:
                ranked_matches.append((score, match))

        # Sort matches by score in descending order
        ranked_matches.sort(reverse=True, key=lambda x: x[0])

        # Prepare and return results if matches found
        if ranked_matches:
            serialized_matches = [
                {"score": score, "data": DataBankGETSerializer(match).data}
                for score, match in ranked_matches
            ]
            return Response(
                {"total_matches": len(ranked_matches), "matches": serialized_matches},
                status=status.HTTP_200_OK,
            )

        # No Matches Found - Notify Ground-Level Staff
        ground_staff_emails = Ground_level_managers_reg.objects.values_list("email", flat=True)
        if ground_staff_emails:
            subject = "⚠️ No Matches Found for New Property"
            message = (
                f"A new property has been added but no matching properties were found.\n\n"
                f"--- Property Details ---\n"
                f"ID: {new_property.id}\n"
                f"Name: {new_property.name}\n"
                f"Phone: {new_property.phonenumber}\n"
                f"Email: {new_property.email}\n"
                f"Purpose: {new_property.purpose}\n"
                f"Type: {new_property.mode_of_property}\n"
                f"District: {new_property.district}\n"
                f"Place: {new_property.place}\n"
                f"Address: {new_property.address}\n"
                f"Demand Price: {new_property.demand_price}\n"
                f"Proposal District: {new_property.location_proposal_district}\n"
                f"Proposal Place: {new_property.location_proposal_place}\n"
                f"Area: {new_property.area_in_sqft}\n"
                f"BHK: {new_property.building_bhk}\n"
                f"Floors: {new_property.number_of_floors}\n"
                f"Roof Type: {new_property.building_roof}\n"
                f"Location Link: {new_property.location_link}\n"
                f"Additional Note: {new_property.additional_note}\n"
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                list(ground_staff_emails),
                fail_silently=True
            )

        return Response(
            {"message": "⚠️ No matching properties found! Email notification sent to Ground-Level Staff."},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    

@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def lead_into_databank(request,lead_id):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)
    databank = DataBank.objects.filter(lead_id=lead_id)
    serializer = DataBankGETSerializer(databank,many=True).data
    return Response(serializer,status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def databank_graph(request):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)
    total_datas = DataBank.objects.all().count()
    for_buy = DataBank.objects.filter(purpose='For Buying a Property').count()
    for_sell = DataBank.objects.filter(purpose='For Selling a Property').count()
    for_rent = DataBank.objects.filter(purpose='For Rental or Lease').count()
    rental_seeker = DataBank.objects.filter(purpose='Looking to rent or Lease property').count()

    response_data = {
        "total_collections": total_datas,
        "sell": for_sell,
        "buy": for_buy,
        "for_rental": for_rent,
        "rental_seeker": rental_seeker
    }
    return Response(response_data, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def Buy_databank(request):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)
    buy_list = DataBank.objects.filter(purpose = "For Buying a Property")
    serializer = DataBankGETSerializer(buy_list,many=True).data
    return Response(serializer,status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def Sell_databank(request):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)
    buy_list = DataBank.objects.filter(purpose = "For Selling a Property")
    serializer = DataBankGETSerializer(buy_list,many=True).data
    return Response(serializer,status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def ForRent_databank(request):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)
    buy_list = DataBank.objects.filter(purpose = "For Rental or Lease")
    serializer = DataBankGETSerializer(buy_list,many=True).data
    return Response(serializer,status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def RentSeeker_databank(request):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)
    buy_list = DataBank.objects.filter(purpose = "Looking to rent or Lease property")
    serializer = DataBankGETSerializer(buy_list,many=True).data
    return Response(serializer,status=200)




@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def SalesM_Buy_databank(request):
    staff = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(staff, 'sales_manager_reg'):
        return Response({"error": "Not a valid sales manager"}, status=403)
    
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    buy_list = DataBank.objects.filter(purpose = "For Buying a Property",follower=salesmanager)
    serializer = DataBankGETSerializer(buy_list,many=True).data
    return Response(serializer,status=200)



@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def SalesM_Sell_databank(request):
    staff = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(staff, 'sales_manager_reg'):
        return Response({"error": "Not a valid sales manager"}, status=403)
    
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    sell_list = DataBank.objects.filter(purpose = "For Selling a Property",follower=salesmanager)
    serializer = DataBankGETSerializer(sell_list,many=True).data
    return Response(serializer,status=200)




@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def SalesM_ForRent_databank(request):
    staff = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(staff, 'sales_manager_reg'):
        return Response({"error": "Not a valid sales manager"}, status=403)
    
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    rental_list = DataBank.objects.filter(purpose = "For Rental or Lease",follower=salesmanager)
    serializer = DataBankGETSerializer(rental_list,many=True).data
    return Response(serializer,status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def SalesM_RentSeeker_databank(request):
    staff = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(staff, 'sales_manager_reg'):
        return Response({"error": "Not a valid sales manager"}, status=403)
    
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    seeker_list = DataBank.objects.filter(purpose = "Looking to rent or Lease Property",follower=salesmanager)
    serializer = DataBankGETSerializer(seeker_list,many=True).data
    return Response(serializer,status=200)




@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def single_databank(request,databank_id):
    staff = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(staff, 'sales_manager_reg'):
        return Response({"error": "Not a valid sales manager"}, status=403)
    
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    databank = DataBank.objects.filter(id=databank_id,follower=salesmanager)
    serializer = DataBankGETSerializer(databank,many=True).data
    return Response(serializer,status=status.HTTP_200_OK)




@api_view(['POST'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def add_image_databank(request,databank_id):
    staff = request.user

    # Check if the user is a sales manager
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    if not salesmanager:
        return Response({"error": "Not a valid sales manager"}, status=status.HTTP_403_FORBIDDEN)

    # Retrieve the databank entry
    try:
        databank = DataBank.objects.get(id=databank_id, follower=salesmanager)
    except DataBank.DoesNotExist:
        return Response({"error": "Databank not available or unauthorized access"}, status=status.HTTP_404_NOT_FOUND)

    # Check if images are present in the request
    images = request.FILES.getlist('photos')  # `getlist` handles multiple images
    if not images:
        return Response({"error": "No images provided"}, status=status.HTTP_400_BAD_REQUEST)

    # Save images
    image_instances = []
    for image in images:
        img_instance = DataBankImage(databank=databank, image=image)
        img_instance.save()
        image_instances.append(img_instance)

    serializer = DataBankImageSerializer(image_instances, many=True)
    return Response(serializer.data, status=status.HTTP_201_CREATED)




@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def view_images_databank(request, databank_id):
    staff = request.user

    # Check if the user is a sales manager
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    if not salesmanager:
        return Response({"error": "Not a valid sales manager"}, status=status.HTTP_403_FORBIDDEN)

    # Retrieve the databank entry
    try:
        databank = DataBank.objects.get(id=databank_id, follower=salesmanager)
    except DataBank.DoesNotExist:
        return Response({"error": "Databank not available or unauthorized access"}, status=status.HTTP_404_NOT_FOUND)

    # Fetch all images for the given databank
    images = DataBankImage.objects.filter(databank=databank)
    if not images.exists():
        return Response({"message": "No images available for this databank"}, status=status.HTTP_404_NOT_FOUND)

    # Serialize and return image data
    serializer = DataBankImageSerializer(images, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)




@api_view(['DELETE'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def delete_image(request, databank_id, image_id):
    staff = request.user

    # Check if the user is a sales manager
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    if not salesmanager:
        return Response({"error": "Not a valid sales manager"}, status=status.HTTP_403_FORBIDDEN)

    # Check if the databank exists and belongs to the sales manager
    try:
        databank = DataBank.objects.get(id=databank_id, follower=salesmanager)
    except DataBank.DoesNotExist:
        return Response({"error": "Databank not available or unauthorized access"}, status=status.HTTP_404_NOT_FOUND)

    # Retrieve the image
    image = get_object_or_404(DataBankImage, id=image_id, databank=databank)

    # Delete the image
    image.delete()
    
    return Response({"message": "Image deleted successfully"}, status=status.HTTP_200_OK)











@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def lead_into_databank_salesmanager(request,lead_id):
    staff = request.user

    # Check if the user is a sales manager
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    if not salesmanager:
        return Response({"error": "Not a valid sales manager"}, status=status.HTTP_403_FORBIDDEN)
    databank = DataBank.objects.filter(lead_id=lead_id)
    serializer = DataBankGETSerializer(databank,many=True).data
    return Response(serializer,status=status.HTTP_200_OK)








@api_view(['GET'])
@permission_classes([IsAuthenticated,IsSalesManagerUser])
def salesmanager_databank_graph(request):
    staff = request.user

    # Check if the user is a sales manager
    salesmanager = Sales_manager_reg.objects.filter(user=staff.id).first()
    if not salesmanager:
        return Response({"error": "Not a valid sales manager"}, status=status.HTTP_403_FORBIDDEN)
    total_datas = DataBank.objects.filter(follower=salesmanager).count()
    for_buy = DataBank.objects.filter(follower=salesmanager, purpose='For Buying a Property').count()
    for_sell = DataBank.objects.filter(follower=salesmanager, purpose='For Selling a Property').count()
    for_rent = DataBank.objects.filter(follower=salesmanager, purpose='For Rental or Lease').count()
    rental_seeker = DataBank.objects.filter(follower=salesmanager, purpose='Looking to Rent or Lease property').count()

    response_data = {
        "total_collections": total_datas,
        "sell": for_sell,
        "buy": for_buy,
        "for_rental": for_rent,
        "rental_seeker": rental_seeker
    }
    return Response(response_data, status=200)




@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def admin_single_databank(request,databank_id):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)
    
    databank = DataBank.objects.filter(id=databank_id)
    serializer = DataBankGETSerializer(databank,many=True).data
    return Response(serializer,status=status.HTTP_200_OK)





@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def admin_view_images_databank(request, databank_id):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)

    # Retrieve the databank entry
    try:
        databank = DataBank.objects.get(id=databank_id)
    except DataBank.DoesNotExist:
        return Response({"error": "Databank not available or unauthorized access"}, status=status.HTTP_404_NOT_FOUND)

    # Fetch all images for the given databank
    images = DataBankImage.objects.filter(databank=databank)
    if not images.exists():
        return Response({"message": "No images available for this databank"}, status=status.HTTP_404_NOT_FOUND)

    # Serialize and return image data
    serializer = DataBankImageSerializer(images, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def lead_into_databank_admin(request,lead_id):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)

    databank = DataBank.objects.filter(lead_id=lead_id)
    serializer = DataBankGETSerializer(databank,many=True).data
    return Response(serializer,status=status.HTTP_200_OK)








@api_view(['GET'])
@permission_classes([IsAuthenticated,IsCustomAdminUser])
def Databank_List_admin(request):
    admin = request.user  # `request.user` will be automatically populated with the authenticated user

    # Check if the user is an admin
    if not hasattr(admin, 'admin_reg'):
        return Response({'error': 'Admin authentication required'}, status=status.HTTP_403_FORBIDDEN)

    databank = DataBank.objects.filter(lead__stage__in=['Not Opened','Data Saved'])
    serializer = DataBankGETSerializer(databank,many=True).data
    return Response(serializer,status=status.HTTP_200_OK)



