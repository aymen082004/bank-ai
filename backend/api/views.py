from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import bcrypt
import jwt
import os
from dotenv import load_dotenv
import datetime
from google.oauth2 import id_token
from google.auth.transport import requests

from .mongodb import get_users_collection, get_customers_collection

load_dotenv()

JWT_SECRET = os.getenv('JWT_SECRET')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

def generate_jwt(user_dict):
    payload = {
        'userId': str(user_dict['_id']),
        'role': user_dict.get('role', ''),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

@api_view(['POST'])
def register(request):
    data = request.data
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email', '')
    cin = data.get('cin', '')
    role = 'customer'
    password = data.get('password')

    if not all([name, password]) or not (phone or email):
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

    users_collection = get_users_collection()
    customers_collection = get_customers_collection()

    # Check if user already exists
    if email and users_collection.find_one({'email': email}):
        return Response({'error': 'User already exists with this email'}, status=status.HTTP_400_BAD_REQUEST)
    if phone and users_collection.find_one({'phone': phone}):
        return Response({'error': 'User already exists with this phone number'}, status=status.HTTP_400_BAD_REQUEST)

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    new_user = {
        'name': name,
        'phone': phone,
        'email': email,
        'cin': cin,
        'role': role,
        'password': hashed_password,
        'created_at': datetime.datetime.utcnow()
    }

    if cin:
        customer = customers_collection.find_one({'personal_info.cin': cin})
        if customer:
            new_user['customer_id'] = str(customer['_id'])

    result = users_collection.insert_one(new_user)
    new_user['_id'] = result.inserted_id
    
    token = generate_jwt(new_user)
    
    return Response({
        'token': token,
        'user': {
            'id': str(new_user['_id']), 
            'name': name, 
            'role': role,
            'email': email,
            'cin': new_user.get('cin', ''),
            'customer_id': new_user.get('customer_id', ''),
            'picture': new_user.get('picture', '')
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def login(request):
    data = request.data
    identifier = data.get('identifier') 
    password = data.get('password')

    users_collection = get_users_collection()
    user = users_collection.find_one({'$or': [{'email': identifier}, {'phone': identifier}]})

    if not user or 'password' not in user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    token = generate_jwt(user)

    return Response({
        'token': token,
        'user': {
            'id': str(user['_id']), 
            'name': user.get('name'), 
            'role': user.get('role'),
            'email': user.get('email', ''),
            'cin': user.get('cin', ''),
            'customer_id': user.get('customer_id', ''),
            'picture': user.get('picture', '')
        }
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
def google_auth(request):
    data = request.data
    token = data.get('token')
    
    try:
        import requests as httprequests
        user_info_response = httprequests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if user_info_response.status_code != 200:
            return Response({'error': 'Invalid Google token'}, status=status.HTTP_401_UNAUTHORIZED)
            
        idinfo = user_info_response.json()
        google_id = idinfo.get('sub')
        email = idinfo.get('email', '')
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')
        google_access_token = token 
        
        users_collection = get_users_collection()
        customers_collection = get_customers_collection()
        
        query = [{ 'googleId': google_id }]
        if email: query.append({ 'email': email })
            
        user = users_collection.find_one({'$or': query})

        role = 'customer'
        phone = data.get('phone')
        cin = data.get('cin', '')
        
        if not user:
            if not phone or not cin:
                return Response({
                    'requiresRole': True,
                    'email': email,
                    'name': name,
                    'picture': picture
                }, status=status.HTTP_200_OK)
            
            new_user = {
                'googleId': google_id,
                'email': email,
                'name': name,
                'role': role,
                'phone': phone,
                'cin': cin,
                'google_access_token': google_access_token,
                'picture': picture,
                'created_at': datetime.datetime.utcnow()
            }
            
            if cin:
                customer = customers_collection.find_one({'personal_info.cin': cin})
                if customer:
                    new_user['customer_id'] = str(customer['_id'])

            result = users_collection.insert_one(new_user)
            new_user['_id'] = result.inserted_id
            user = new_user
        else:
            update_data = {}
            if not user.get('googleId'): update_data['googleId'] = google_id
            if not user.get('picture'): update_data['picture'] = picture
            if not user.get('email'): update_data['email'] = email
            update_data['google_access_token'] = google_access_token
            
            if update_data:
                users_collection.update_one({'_id': user['_id']}, {'$set': update_data})
                user.update(update_data)

        auth_token = generate_jwt(user)
        return Response({
            'token': auth_token,
            'user': {
                'id': str(user['_id']), 
                'name': user.get('name'), 
                'role': user.get('role'),
                'email': user.get('email', ''),
                'cin': user.get('cin', ''),
                'customer_id': user.get('customer_id', ''),
                'picture': user.get('picture', '')
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
         return Response({'error': 'Exception during Google Auth verification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
