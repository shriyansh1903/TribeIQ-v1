import pandas as pd
from typing import List, Dict, Any

class WardenMapper:
    """
    Maps raw Warden API responses into the exact schema and structures
    expected by TribeIQ's downstream cleaner, feature engineering,
    and profile generation pipelines.
    """
    @staticmethod
    def map_to_residents_dataframe(
        raw_residents: List[Dict[str, Any]], 
        raw_bookings: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Combines and maps Warden Residents and Bookings JSON payloads
        into a single Pandas DataFrame matching the exact layout of data/Residents.csv.
        """
        # Index bookings by resident_id for fast lookup
        bookings_by_res: Dict[str, Dict[str, Any]] = {}
        for b in raw_bookings:
            res_id = str(b.get("resident_id", ""))
            if res_id:
                # Store the most relevant or approved booking
                if res_id not in bookings_by_res or b.get("status") == "Approved":
                    bookings_by_res[res_id] = b

        rows = []
        for res in raw_residents:
            res_id = str(res.get("id", ""))
            booking = bookings_by_res.get(res_id, {})
            
            # Map values matching the exact column names of data/Residents.csv
            row = {
                "Resident ID": res.get("id"),
                "User ID": res.get("user_id"),
                "Booking ID": booking.get("booking_id", ""),
                "Channel": "",
                "Name": res.get("name"),
                "Phone": res.get("phone"),
                "Email": res.get("email"),
                "Gender": res.get("gender"),
                "Type": res.get("type", "Student"),
                "Status": res.get("status", "Approved"),
                "Extending": "No",
                "Property": res.get("property_name", booking.get("property_name", "")),
                "Room Type": booking.get("room_type", "Twin"),
                "Room": booking.get("room_number", ""),
                "Beds": booking.get("bed_letter", ""),
                "Bed Count": 1,
                "Move In Date": booking.get("move_in_date", ""),
                "Move Out Date": booking.get("move_out_date", ""),
                "Term End Date": booking.get("move_out_date", ""),
                "App Downloaded": "Yes",
                "Agreement Signed": "Yes",
                "Tax Number": "",
                "Company Name": "",
                "Company Address": "",
                "Wifi Status": "Active",
                "Wifi Username": res.get("id"),
                "Payment Plan": "",
                "Security Deposit": booking.get("deposit", 15000.0),
                "Rent": booking.get("rent", 15000.0),
                "Maintenance": 0.0,
                "Registration Form": "Uploaded",
                "College Name": "",
                "Admission Year": "",
                "College ID Number": "",
                "College ID (Image)": "",
                "Course Name": "",
                "Course Year": "",
                "Office Location": "",
                "Employee ID": "",
                "Employee ID (Image)": "",
                "Department": "",
                "Job Profile": "",
                "Passport Size Photo": "Uploaded",
                "Aadhar": "Uploaded",
                "PAN Card": "Uploaded",
                "Interests": res.get("interests", "[]"),
                "Any Suggestions": "",
                "Date Of Birth": res.get("dob"),
                "Home Address": res.get("home_address", ""),
                "Hometown": res.get("hometown", ""),
                "Pincode": res.get("pincode", ""),
                "Parent 1 Name": "",
                "Relation with Parent 1": "",
                "Parent 1 Number": "",
                "Parent 2 Name": "",
                "Relation with Parent 2": "",
                "Parent 2 Number": "",
                "Guardian Name": "",
                "Relation": "",
                "Guardian Number": "",
                "Emergency Contact": "",
                "Food Preference": "Veg",
                "Blood Group": "B+",
                "Allergies": "None",
                "Other medical details": "None",
                "Instagram Handle": "",
                "Feedback Form": "",
                "Sad to see you go! Why though?": "",
                "Please Rate the Housekeeping ": "",
                "Please Rate the Staff services": "",
                "How much did you enjoy the Amenities?": "",
                "How was your Overall Experience?": "",
                "Will you recommend us ?": "",
                "How was the community experience?": "",
                "Any suggestions that would’ve made your stay better?": "",
                "How was the Food?": "",
                "Any special shout-outs to any of our staff?": "",
                "Bank Account Number": "",
                "Bank IFSC Code": "",
                "Bank Name": "",
                "Account Holder Name": ""
            }
            rows.append(row)

        df_mapped = pd.DataFrame(rows)
        return df_mapped
