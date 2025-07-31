# Railway deployment entry point - Complete FastAPI app
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, date as dt_date
from typing import Optional, List
import uuid
import json

# Import backend modules
try:
    from database import init_database, create_default_users, close_database
    from models import User, Driver, Passenger, Admin, Ride, KilometerEntry, FuelEntry, LeaveRequest, DriverAttendance, RideStatus, LeaveRequestStatus, Vehicle
    from config import settings
    from auth import get_password_hash, verify_password, create_access_token, get_current_user, get_current_admin, get_current_driver
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"🔍 Backend path: {backend_path}")
    print(f"🔍 Current working directory: {os.getcwd()}")
    print(f"🔍 Files in backend: {list(backend_path.glob('*.py')) if backend_path.exists() else 'Directory not found'}")
    raise

# Create FastAPI app
app = FastAPI(title="RideShare API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    await init_database()
    await create_default_users()
    print("✅ MongoDB Atlas connected and ready!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    await close_database()

# Test endpoint
@app.get("/test")
async def test_endpoint():
    return {"message": "Backend is working with MongoDB Atlas!", "status": "success"}

# Simple test endpoint for mobile app
@app.get("/mobile-test")
async def mobile_test():
    """Simple test endpoint for mobile app connectivity"""
    return {
        "status": "success",
        "message": "Mobile app can reach the server!",
        "timestamp": datetime.utcnow().isoformat(),
        "server": "RecTransport Backend"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "message": "RecTransport API is running",
        "timestamp": datetime.utcnow().isoformat()
    }

# Debug endpoints (no authentication required)
@app.get("/debug/data")
async def debug_data():
    """Debug endpoint to check all data without authentication"""
    try:
        # Get all users
        users = await User.find_all().to_list()
        drivers = await Driver.find_all().to_list()
        passengers = await Passenger.find_all().to_list()
        vehicles = await Vehicle.find_all().to_list()
        
        return {
            "status": "success",
            "data": {
                "users_count": len(users),
                "drivers_count": len(drivers),
                "passengers_count": len(passengers),
                "vehicles_count": len(vehicles),
                "users": [{"id": u.id, "name": u.name, "email": u.email, "role": u.role} for u in users],
                "drivers": [{"id": d.id, "user_id": d.user_id, "vehicle_make": d.vehicle_make, "license_plate": d.license_plate} for d in drivers],
                "passengers": [{"id": p.id, "user_id": p.user_id} for p in passengers],
                "vehicles": [{"id": v.id, "vehicle_make": v.vehicle_make, "license_plate": v.license_plate} for v in vehicles]
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/debug/users")
async def debug_users():
    """Get all users without authentication"""
    try:
        users = await User.find_all().to_list()
        return {
            "status": "success",
            "users": [
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
                for user in users
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/debug/users-simple")
async def debug_users_simple():
    """Get all users in simple format without authentication"""
    try:
        users = await User.find_all().to_list()
        return {
            "status": "success",
            "users": [
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role
                }
                for user in users
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/debug/drivers")
async def debug_drivers():
    """Get all drivers without authentication (for testing)"""
    try:
        print("🔍 Debug: Fetching all drivers...")
        drivers = await Driver.find_all().to_list()
        
        # Get user info for each driver
        driver_list = []
        for driver in drivers:
            try:
                user = await User.get(driver.user_id)
                driver_data = {
                    "id": str(driver.id),
                    "user_id": str(driver.user_id),
                    "user_name": user.name if user else "Unknown",
                    "user_email": user.email if user else "Unknown",
                    "user_phone": user.phone if user else "Unknown",
                    "vehicle_make": driver.vehicle_make,
                    "vehicle_model": driver.vehicle_model,
                    "vehicle_year": driver.vehicle_year,
                    "license_plate": driver.license_plate,
                    "vehicle_color": driver.vehicle_color,
                    "license_number": driver.license_number,
                    "license_expiry": driver.license_expiry.isoformat() if driver.license_expiry else None,
                    "rating": driver.rating,
                    "total_rides": driver.total_rides,
                    "current_km_reading": driver.current_km_reading,
                    "is_online": driver.is_online,
                    "created_at": getattr(driver, 'created_at', None),
                    "updated_at": getattr(driver, 'updated_at', None)
                }
                
                # Convert datetime objects to ISO format if they exist
                if driver_data["created_at"]:
                    driver_data["created_at"] = driver_data["created_at"].isoformat()
                if driver_data["updated_at"]:
                    driver_data["updated_at"] = driver_data["updated_at"].isoformat()
                
                driver_list.append(driver_data)
            except Exception as e:
                print(f"❌ Error processing driver {driver.id}: {e}")
                continue
        
        print(f"✅ Debug: Found {len(driver_list)} drivers")
        return {"status": "success", "drivers": driver_list}
    except Exception as e:
        print(f"❌ Debug: Error fetching drivers: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/debug/vehicles")
async def debug_vehicles():
    """Get all vehicles without authentication (for testing)"""
    try:
        print("🔍 Debug: Fetching all vehicles...")
        
        # Get vehicles created directly
        vehicles = await Vehicle.find_all().to_list()
        vehicle_list = []
        
        for vehicle in vehicles:
            vehicle_data = {
                "id": str(vehicle.id),
                "vehicle_make": vehicle.vehicle_make,
                "vehicle_model": vehicle.vehicle_model,
                "vehicle_year": vehicle.vehicle_year,
                "license_plate": vehicle.license_plate,
                "vehicle_color": vehicle.vehicle_color,
                "license_number": vehicle.license_number,
                "license_expiry": vehicle.license_expiry.isoformat() if vehicle.license_expiry else None,
                "created_at": getattr(vehicle, 'created_at', None),
                "updated_at": getattr(vehicle, 'updated_at', None)
            }
            
            # Convert datetime objects to ISO format if they exist
            if vehicle_data["created_at"]:
                vehicle_data["created_at"] = vehicle_data["created_at"].isoformat()
            if vehicle_data["updated_at"]:
                vehicle_data["updated_at"] = vehicle_data["updated_at"].isoformat()
            
            vehicle_list.append(vehicle_data)
        
        # Get vehicles from drivers
        drivers = await Driver.find_all().to_list()
        for driver in drivers:
            if (driver.vehicle_make and driver.vehicle_model and 
                driver.license_plate and driver.vehicle_color):
                try:
                    user = await User.get(driver.user_id)
                    vehicle_data = {
                        "id": f"driver_{str(driver.id)}",
                        "driver_id": str(driver.id),
                        "driver_name": user.name if user else "Unknown",
                        "vehicle_make": driver.vehicle_make,
                        "vehicle_model": driver.vehicle_model,
                        "vehicle_year": driver.vehicle_year,
                        "license_plate": driver.license_plate,
                        "vehicle_color": driver.vehicle_color,
                        "license_number": driver.license_number,
                        "license_expiry": driver.license_expiry.isoformat() if driver.license_expiry else None,
                        "created_at": getattr(driver, 'created_at', None),
                        "updated_at": getattr(driver, 'updated_at', None)
                    }
                    
                    # Convert datetime objects to ISO format if they exist
                    if vehicle_data["created_at"]:
                        vehicle_data["created_at"] = vehicle_data["created_at"].isoformat()
                    if vehicle_data["updated_at"]:
                        vehicle_data["updated_at"] = vehicle_data["updated_at"].isoformat()
                    
                    vehicle_list.append(vehicle_data)
                except Exception as e:
                    print(f"❌ Error processing driver vehicle {driver.id}: {e}")
                    continue
        
        print(f"✅ Debug: Found {len(vehicle_list)} vehicles")
        return {"status": "success", "vehicles": vehicle_list}
    except Exception as e:
        print(f"❌ Debug: Error fetching vehicles: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/debug/rides")
async def debug_rides():
    """Get all rides without authentication (for testing)"""
    try:
        print("🔍 Debug: Fetching all rides...")
        rides = await Ride.find_all().to_list()
        
        print(f"✅ Debug: Found {len(rides)} rides")
        
        ride_list = []
        for ride in rides:
            ride_data = {
                "id": str(ride.id),
                "passenger_id": ride.passenger_id,
                "driver_id": ride.driver_id,
                "status": ride.status,
                "pickup_address": ride.pickup_address,
                "dropoff_address": ride.dropoff_address,
                "requested_at": ride.requested_at.isoformat() if ride.requested_at else None,
                "assigned_at": ride.assigned_at.isoformat() if ride.assigned_at else None,
                "picked_up_at": ride.picked_up_at.isoformat() if ride.picked_up_at else None,
                "completed_at": ride.completed_at.isoformat() if ride.completed_at else None,
                "distance": ride.distance,
                "start_km": ride.start_km,
                "end_km": ride.end_km
            }
            ride_list.append(ride_data)
        
        return {"status": "success", "rides": ride_list}
    except Exception as e:
        print(f"❌ Debug: Error fetching rides: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/debug/fuel-entries")
async def debug_fuel_entries():
    """Get all fuel entries without authentication (for testing)"""
    try:
        print("🔍 Debug: Fetching all fuel entries...")
        fuel_entries = await FuelEntry.find_all().to_list()
        
        # Get driver info for each fuel entry
        fuel_list = []
        for entry in fuel_entries:
            try:
                driver = await Driver.get(entry.driver_id)
                user = None
                if driver:
                    user = await User.get(driver.user_id)
                
                fuel_data = {
                    "id": str(entry.id),
                    "driver_id": str(entry.driver_id),
                    "driver_name": user.name if user else "Unknown",
                    "vehicle_make": driver.vehicle_make if driver else "Unknown",
                    "license_plate": driver.license_plate if driver else "Unknown",
                    "fuel_amount": entry.fuel_amount,
                    "fuel_cost": entry.fuel_cost,
                    "fuel_type": entry.fuel_type,
                    "odometer_reading": entry.odometer_reading,
                    "fuel_station": entry.fuel_station,
                    "date": entry.date.isoformat() if entry.date else None,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None
                }
                fuel_list.append(fuel_data)
            except Exception as e:
                print(f"❌ Error processing fuel entry {entry.id}: {e}")
                continue
        
        print(f"✅ Debug: Found {len(fuel_list)} fuel entries")
        return {"status": "success", "fuel_entries": fuel_list}
    except Exception as e:
        print(f"❌ Debug: Error fetching fuel entries: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/debug/rides-with-details")
async def debug_get_rides_with_details():
    """Get all rides with passenger and driver details for admin"""
    try:
        # Fetch all rides
        rides = await Ride.find_all().to_list()
        
        # Collect all passenger and driver IDs
        passenger_ids = [ride.passenger_id for ride in rides if ride.passenger_id]
        driver_ids = [ride.driver_id for ride in rides if ride.driver_id]
        
        # Fetch passengers
        passengers = {p.id: p async for p in Passenger.find({"_id": {"$in": passenger_ids}})}
        
        # Fetch drivers
        drivers = {d.id: d async for d in Driver.find({"_id": {"$in": driver_ids}})}
        
        # Fetch all user IDs for passengers and drivers
        passenger_user_ids = [p.user_id for p in passengers.values()]
        driver_user_ids = [d.user_id for d in drivers.values()]
        all_user_ids = list(set(passenger_user_ids + driver_user_ids))
        
        # Fetch all users
        users = {str(u.id): u async for u in User.find({"_id": {"$in": all_user_ids}})}
        
        # Create response with full details
        ride_responses = []
        for ride in rides:
            passenger = passengers.get(ride.passenger_id)
            driver = drivers.get(ride.driver_id) if ride.driver_id else None
            
            passenger_user = None
            driver_user = None
            
            if passenger:
                passenger_user = users.get(str(passenger.user_id))
            if driver:
                driver_user = users.get(str(driver.user_id))
            
            # Create ride response with full details
            ride_response = {
                "id": str(ride.id),
                "passenger_id": ride.passenger_id,
                "driver_id": ride.driver_id,
                "status": ride.status,
                "pickup_latitude": ride.pickup_latitude,
                "pickup_longitude": ride.pickup_longitude,
                "pickup_address": ride.pickup_address,
                "dropoff_latitude": ride.dropoff_latitude,
                "dropoff_longitude": ride.dropoff_longitude,
                "dropoff_address": ride.dropoff_address,
                "requested_at": ride.requested_at.isoformat() if ride.requested_at else None,
                "assigned_at": ride.assigned_at.isoformat() if ride.assigned_at else None,
                "picked_up_at": ride.picked_up_at.isoformat() if ride.picked_up_at else None,
                "completed_at": ride.completed_at.isoformat() if ride.completed_at else None,
                "distance": ride.distance,
                "start_km": ride.start_km,
                "end_km": ride.end_km,
                "passenger": {
                    "id": str(passenger.id) if passenger else None,
                    "user_id": passenger.user_id if passenger else None,
                    "rating": passenger.rating if passenger else 0.0,
                    "total_rides": passenger.total_rides if passenger else 0,
                    "user": {
                        "id": str(passenger_user.id) if passenger_user else None,
                        "name": passenger_user.name if passenger_user else "Unknown",
                        "email": passenger_user.email if passenger_user else "No email",
                        "phone": passenger_user.phone if passenger_user else "No phone",
                        "role": passenger_user.role if passenger_user else "passenger",
                        "avatar": passenger_user.avatar if passenger_user else None,
                        "created_at": passenger_user.created_at.isoformat() if passenger_user and passenger_user.created_at else None,
                        "is_active": passenger_user.is_active if passenger_user else True
                    } if passenger_user else None
                } if passenger else None,
                "driver": {
                    "id": str(driver.id) if driver else None,
                    "user_id": driver.user_id if driver else None,
                    "vehicle_make": driver.vehicle_make if driver else None,
                    "vehicle_model": driver.vehicle_model if driver else None,
                    "license_plate": driver.license_plate if driver else None,
                    "is_online": driver.is_online if driver else False,
                    "user": {
                        "id": str(driver_user.id) if driver_user else None,
                        "name": driver_user.name if driver_user else "Unknown",
                        "email": driver_user.email if driver_user else "No email",
                        "phone": driver_user.phone if driver_user else "No phone",
                        "role": driver_user.role if driver_user else "driver",
                        "avatar": driver_user.avatar if driver_user else None,
                        "created_at": driver_user.created_at.isoformat() if driver_user and driver_user.created_at else None,
                        "is_active": driver_user.is_active if driver_user else True
                    } if driver_user else None
                } if driver else None
            }
            ride_responses.append(ride_response)
        
        return {
            "status": "success",
            "rides": ride_responses,
            "total": len(ride_responses)
        }
        
    except Exception as e:
        print(f"Error in debug_get_rides_with_details: {e}")
        return {
            "status": "error",
            "message": str(e),
            "rides": []
        }

# Authentication endpoints
@app.post("/auth/login")
async def login(user_credentials: dict):
    print(f"🔐 Login attempt for email: {user_credentials.get('email')}")
    
    user = await User.find_one({"email": user_credentials.get("email")})
    
    if not user:
        print(f"❌ User not found for email: {user_credentials.get('email')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"✅ User found: {user.name} (role: {user.role})")
    
    if not verify_password(user_credentials.get("password"), user.password_hash):
        print(f"❌ Password verification failed for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"✅ Password verified successfully for user: {user.email}")
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    print(f"🎉 Login successful for user: {user.name}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# User management endpoints (admin only)
@app.post("/users")
async def create_user(user_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a new user (admin only)"""
    # Check if user with this email already exists
    existing_user = await User.find_one({"email": user_data.get("email")})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create new user
    new_user = User(
        name=user_data.get("name"),
        email=user_data.get("email"),
        phone=user_data.get("phone"),
        role=user_data.get("role"),
        password_hash=get_password_hash("password"),  # Default password
    )
    await new_user.insert()
    
    return new_user

@app.post("/drivers")
async def create_driver(driver_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a new driver (admin only)"""
    # Check if user with this email already exists
    existing_user = await User.find_one({"email": driver_data.get("user", {}).get("email")})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create user first
    new_user = User(
        name=driver_data.get("user", {}).get("name"),
        email=driver_data.get("user", {}).get("email"),
        phone=driver_data.get("user", {}).get("phone"),
        role="driver",
        password_hash=get_password_hash("password"),  # Default password
    )
    await new_user.insert()
    
    # Create driver profile (without vehicle info)
    driver_profile = await Driver.create_driver(
        user_id=new_user.id,
        license_number=driver_data.get("license_number"),
        license_expiry=driver_data.get("license_expiry"),
        rating=driver_data.get("rating", 5.0),
        total_rides=driver_data.get("total_rides", 0),
        current_km_reading=driver_data.get("current_km_reading", 0)
    )
    
    return driver_profile

@app.post("/passengers")
async def create_passenger(passenger_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a new passenger (admin only)"""
    # Check if user with this email already exists
    existing_user = await User.find_one({"email": passenger_data.get("user", {}).get("email")})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create user first
    new_user = User(
        name=passenger_data.get("user", {}).get("name"),
        email=passenger_data.get("user", {}).get("email"),
        phone=passenger_data.get("user", {}).get("phone"),
        role="passenger",
        password_hash=get_password_hash("password"),  # Default password
    )
    await new_user.insert()
    
    # Create passenger profile
    passenger_profile = Passenger(
        user_id=new_user.id,
        rating=passenger_data.get("rating", 5.0),
        total_rides=passenger_data.get("total_rides", 0)
    )
    await passenger_profile.insert()
    
    return passenger_profile

# Driver management endpoints
@app.get("/drivers")
async def get_all_drivers(current_user: User = Depends(get_current_admin)):
    """Get all drivers (admin only)"""
    drivers = await Driver.find_all().to_list()
    return drivers

@app.get("/passengers")
async def get_all_passengers(current_user: User = Depends(get_current_admin)):
    """Get all passengers (admin only)"""
    passengers = await Passenger.find_all().to_list()
    user_ids = [p.user_id for p in passengers]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}
    response = []
    for p in passengers:
        user = users.get(str(p.user_id))
        passenger_dict = p.dict()
        passenger_dict["user"] = user.dict() if user else None
        response.append(passenger_dict)
    return response

@app.post("/vehicles")
async def create_vehicle(vehicle_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a new vehicle (admin only, not attached to a driver)"""
    print(f"🚗 Creating vehicle with data: {vehicle_data}")
    
    # Validate required fields
    required_fields = [
        "vehicle_make", "vehicle_model", "vehicle_year", "license_plate",
        "vehicle_color", "license_number", "license_expiry"
    ]
    for field in required_fields:
        if not vehicle_data.get(field):
            print(f"❌ Missing required field: {field}")
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Parse license_expiry to datetime
    license_expiry = vehicle_data["license_expiry"]
    if isinstance(license_expiry, str):
        try:
            license_expiry = datetime.strptime(license_expiry, "%d-%m-%Y")
            print(f"✅ Parsed license_expiry: {license_expiry}")
        except Exception as e:
            print(f"❌ Error parsing license_expiry: {e}")
            raise HTTPException(status_code=400, detail="license_expiry must be in DD-MM-YYYY format")
    
    try:
        vehicle = Vehicle(
            vehicle_make=vehicle_data["vehicle_make"],
            vehicle_model=vehicle_data["vehicle_model"],
            vehicle_year=int(vehicle_data["vehicle_year"]),
            license_plate=vehicle_data["license_plate"],
            vehicle_color=vehicle_data["vehicle_color"],
            license_number=vehicle_data["license_number"],
            license_expiry=license_expiry
        )
        await vehicle.insert()
        print(f"✅ Vehicle created successfully with ID: {vehicle.id}")
        return vehicle
    except Exception as e:
        print(f"❌ Error creating vehicle: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create vehicle: {str(e)}")

@app.get("/vehicles")
async def get_all_vehicles(current_user: User = Depends(get_current_admin)):
    """Get all vehicles (admin only) - includes both direct vehicles and driver vehicles"""
    # Vehicles created directly
    vehicles = await Vehicle.find_all().to_list()
    vehicle_list = [
        {
            "id": v.id,
            "vehicle_make": v.vehicle_make,
            "vehicle_model": v.vehicle_model,
            "vehicle_year": v.vehicle_year,
            "license_plate": v.license_plate,
            "vehicle_color": v.vehicle_color,
            "license_number": v.license_number,
            "license_expiry": v.license_expiry.isoformat() if v.license_expiry else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None
        }
        for v in vehicles
    ]
    # Vehicles attached to drivers
    drivers = await Driver.find_all().to_list()
    for driver in drivers:
        if (driver.vehicle_make and driver.vehicle_model and 
            driver.license_plate and driver.vehicle_color):
            vehicle_list.append({
                "id": str(driver.id),
                "vehicle_make": driver.vehicle_make,
                "vehicle_model": driver.vehicle_model,
                "vehicle_year": driver.vehicle_year,
                "license_plate": driver.license_plate,
                "vehicle_color": driver.vehicle_color,
                "license_number": driver.license_number,
                "license_expiry": driver.license_expiry.isoformat() if driver.license_expiry else None,
                "created_at": driver.created_at.isoformat() if hasattr(driver, 'created_at') and driver.created_at else None,
                "updated_at": driver.updated_at.isoformat() if hasattr(driver, 'updated_at') and driver.updated_at else None
            })
    return vehicle_list

# Fuel entries management
@app.get("/fuel-entries")
async def get_fuel_entries(current_user: User = Depends(get_current_admin)):
    """Get all fuel entries (admin only)"""
    try:
        fuel_entries = await FuelEntry.find_all().to_list()
        
        # Get driver info for each fuel entry
        fuel_list = []
        for entry in fuel_entries:
            try:
                driver = await Driver.get(entry.driver_id)
                user = None
                if driver:
                    user = await User.get(driver.user_id)
                
                fuel_data = {
                    "id": str(entry.id),
                    "driver_id": str(entry.driver_id),
                    "driver_name": user.name if user else "Unknown",
                    "vehicle_make": driver.vehicle_make if driver else "Unknown",
                    "license_plate": driver.license_plate if driver else "Unknown",
                    "fuel_amount": entry.fuel_amount,
                    "fuel_cost": entry.fuel_cost,
                    "fuel_type": entry.fuel_type,
                    "odometer_reading": entry.odometer_reading,
                    "fuel_station": entry.fuel_station,
                    "date": entry.date.isoformat() if entry.date else None,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None
                }
                fuel_list.append(fuel_data)
            except Exception as e:
                print(f"❌ Error processing fuel entry {entry.id}: {e}")
                continue
        
        return {"status": "success", "fuel_entries": fuel_list}
    except Exception as e:
        print(f"❌ Error fetching fuel entries: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/fuel-entries")
async def create_fuel_entry(fuel_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a new fuel entry (admin only)"""
    try:
        # Validate required fields
        required_fields = ["driver_id", "fuel_amount", "fuel_cost", "fuel_type", "odometer_reading"]
        for field in required_fields:
            if not fuel_data.get(field):
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Parse date if provided
        fuel_date = fuel_data.get("date")
        if fuel_date and isinstance(fuel_date, str):
            try:
                fuel_date = datetime.strptime(fuel_date, "%Y-%m-%d")
            except:
                fuel_date = datetime.utcnow()
        else:
            fuel_date = datetime.utcnow()
        
        fuel_entry = FuelEntry(
            driver_id=fuel_data["driver_id"],
            fuel_amount=float(fuel_data["fuel_amount"]),
            fuel_cost=float(fuel_data["fuel_cost"]),
            fuel_type=fuel_data["fuel_type"],
            odometer_reading=float(fuel_data["odometer_reading"]),
            fuel_station=fuel_data.get("fuel_station", "Unknown"),
            date=fuel_date
        )
        await fuel_entry.insert()
        
        return {"status": "success", "fuel_entry": fuel_entry}
    except Exception as e:
        print(f"❌ Error creating fuel entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create fuel entry: {str(e)}")

# Ride management
@app.post("/rides")
async def create_ride(ride_data: dict):
    """Create a new ride"""
    new_ride = Ride(
        passenger_id=ride_data.get("passenger_id"),
        pickup_latitude=ride_data.get("pickup_latitude"),
        pickup_longitude=ride_data.get("pickup_longitude"),
        pickup_address=ride_data.get("pickup_address"),
        dropoff_latitude=ride_data.get("dropoff_latitude"),
        dropoff_longitude=ride_data.get("dropoff_longitude"),
        dropoff_address=ride_data.get("dropoff_address"),
        status=RideStatus.REQUESTED
    )
    await new_ride.insert()
    return new_ride

@app.get("/rides")
async def get_rides(passenger_id: Optional[str] = None, driver_id: Optional[str] = None):
    """Get rides with optional filters and populate driver and passenger info"""
    query = {}
    if passenger_id:
        query["passenger_id"] = passenger_id
    if driver_id:
        query["driver_id"] = driver_id

    rides = await Ride.find(query).to_list()

    # Collect all driver and passenger IDs
    driver_ids = [ride.driver_id for ride in rides if ride.driver_id]
    passenger_ids = [ride.passenger_id for ride in rides if ride.passenger_id]

    # Fetch drivers and passengers
    drivers = {d.id: d async for d in Driver.find({"id": {"$in": driver_ids}})}
    passengers = {p.id: p async for p in Passenger.find({"id": {"$in": passenger_ids}})}

    # Fetch all user IDs
    user_ids = [d.user_id for d in drivers.values()] + [p.user_id for p in passengers.values()]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}

    # Attach driver and passenger user info to each ride
    for ride in rides:
        driver = drivers.get(ride.driver_id)
        if driver:
            driver.user = users.get(str(driver.user_id))
            ride.driver = driver
        passenger = passengers.get(ride.passenger_id)
        if passenger:
            passenger.user = users.get(str(passenger.user_id))
            ride.passenger = passenger

    return rides

@app.get("/rides/pending")
async def get_pending_rides(current_user: User = Depends(get_current_admin)):
    """Get all pending rides (admin only)"""
    rides = await Ride.find({"status": RideStatus.REQUESTED}).to_list()
    return rides

@app.get("/rides/assigned")
async def get_assigned_rides(current_user: User = Depends(get_current_driver)):
    """Get rides assigned to current driver"""
    # First, find the driver record for this user
    driver = await Driver.find_one({"user_id": current_user.id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    # Now use the driver.id to find rides
    rides = await Ride.find({"driver_id": driver.id, "status": {"$in": [RideStatus.ASSIGNED, RideStatus.IN_PROGRESS]}}).to_list()
    
    # Collect all passenger IDs
    passenger_ids = [ride.passenger_id for ride in rides if ride.passenger_id]
    
    # Fetch passengers using _id field
    passengers = {p.id: p async for p in Passenger.find({"_id": {"$in": passenger_ids}})}
    
    # Fetch all user IDs for passengers
    user_ids = [p.user_id for p in passengers.values()]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}
    
    # Create response with proper passenger structure
    ride_responses = []
    for ride in rides:
        passenger = passengers.get(ride.passenger_id)
        passenger_user = None
        if passenger:
            passenger_user = users.get(str(passenger.user_id))
        
        # Create ride response with passenger details
        ride_response = {
            "id": str(ride.id),
            "passenger_id": ride.passenger_id,
            "driver_id": ride.driver_id,
            "status": ride.status,
            "pickup_latitude": ride.pickup_latitude,
            "pickup_longitude": ride.pickup_longitude,
            "pickup_address": ride.pickup_address,
            "dropoff_latitude": ride.dropoff_latitude,
            "dropoff_longitude": ride.dropoff_longitude,
            "dropoff_address": ride.dropoff_address,
            "requested_at": ride.requested_at.isoformat() if ride.requested_at else None,
            "assigned_at": ride.assigned_at.isoformat() if ride.assigned_at else None,
            "picked_up_at": ride.picked_up_at.isoformat() if ride.picked_up_at else None,
            "completed_at": ride.completed_at.isoformat() if ride.completed_at else None,
            "distance": ride.distance,
            "start_km": ride.start_km,
            "end_km": ride.end_km,
            "passenger": {
                "id": str(passenger.id) if passenger else None,
                "user_id": passenger.user_id if passenger else None,
                "rating": passenger.rating if passenger else 0.0,
                "total_rides": passenger.total_rides if passenger else 0,
                "user": {
                    "id": str(passenger_user.id) if passenger_user else None,
                    "name": passenger_user.name if passenger_user else "Unknown",
                    "email": passenger_user.email if passenger_user else "No email",
                    "phone": passenger_user.phone if passenger_user else "No phone",
                    "role": passenger_user.role if passenger_user else "passenger",
                    "avatar": passenger_user.avatar if passenger_user else None,
                    "created_at": passenger_user.created_at.isoformat() if passenger_user and passenger_user.created_at else None,
                    "is_active": passenger_user.is_active if passenger_user else True
                } if passenger_user else None
            } if passenger else None
        }
        ride_responses.append(ride_response)
    
    return ride_responses

# Railway deployment
if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from Railway environment variable
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Starting RecTransport API server on port {port}")
    print(f"🔗 Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    print(f"📊 MongoDB URL: {os.environ.get('MONGODB_URL', 'Not set')[:50]}...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info"
    ) 