import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVENTS_CSV = PROJECT_ROOT / "data" / "events.csv"

def expand():
    df = pd.read_csv(EVENTS_CSV)
    existing_names = set(df["Event Name"].str.strip().str.lower().tolist())
    
    new_entries = [
        # Flea Market
        ("Retail Pop-up", "Flea Market", "Retail", "Local retail pop-up stalls.", "Engagement", "Student,Working Professional", "Shopping,Social", "Medium", 80, 50, 90, 10, 10, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 5000),
        ("F&B Pop-up", "Flea Market", "Food", "Food pop-up stalls.", "Socializing", "Student,Working Professional", "Food,Social", "Medium", 82, 60, 85, 10, 10, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 6000),
        ("Weekend Market", "Flea Market", "Market", "Weekend community market.", "Integration", "Student,Working Professional", "Social,Shopping", "Large", 80, 45, 88, 10, 15, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 12000),
        ("Local Business Expo", "Flea Market", "Expo", "Expo showcasing local businesses.", "Professional", "Working Professional", "Business,Networking", "Medium", 70, 90, 60, 40, 10, "Yes", "Yes", "No", "Yes", "Quarterly", "Major", "All", 8000),
        ("Handmade Market", "Flea Market", "Crafts", "Market for handmade products.", "Creativity", "Student,Working Professional", "Art,Crafts", "Medium", 78, 50, 80, 15, 10, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 5000),
        ("Farmers Market", "Flea Market", "Market", "Fresh local farm produce market.", "Wellbeing", "Student,Working Professional", "Health,Food", "Large", 75, 40, 80, 20, 20, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 7000),

        # Food & Beverage
        ("Coffee Festival", "Food & Beverage", "Coffee", "Coffee tasting and brewing sessions.", "Relaxation", "Student,Working Professional", "Coffee,Social", "Medium", 85, 40, 80, 60, 10, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 9000),
        ("Dessert Festival", "Food & Beverage", "Dessert", "Delicious desserts from local vendors.", "Fun", "Student,Working Professional", "Food,Desserts", "Medium", 88, 45, 92, 10, 10, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 10000),
        ("Street Food Festival", "Food & Beverage", "Street Food", "Diverse street food offerings.", "Engagement", "Student,Working Professional", "Food,Social", "Large", 82, 50, 90, 10, 10, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 15000),
        ("Food Carnival", "Food & Beverage", "Carnival", "Games, stalls, and lots of food.", "Entertainment", "Student,Working Professional", "Food,Games", "Large", 80, 55, 95, 10, 20, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 18000),
        ("Brunch Pop-up", "Food & Beverage", "Brunch", "Sunday morning premium brunch.", "Socializing", "Working Professional", "Food,Social", "Medium", 75, 70, 75, 10, 10, "Yes", "Yes", "No", "Yes", "Monthly", "Minor", "All", 8000),
        ("Regional Cuisine Night", "Food & Beverage", "Cultural Food", "Regional cuisine themed dinner.", "Cultural exchange", "Student,Working Professional", "Food,Culture", "Large", 78, 55, 88, 15, 5, "Yes", "Yes", "Yes", "Yes", "Monthly", "Major", "All", 5000),
        ("Healthy Food Fair", "Food & Beverage", "Health", "Nutritious organic meals and fair.", "Wellbeing", "Student,Working Professional", "Fitness,Wellness", "Medium", 70, 45, 75, 30, 20, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Minor", "All", 6000),

        # Retail
        ("Sneaker Pop-up", "Retail", "Footwear", "Exhibition of limited edition sneakers.", "Branding", "Student,Working Professional", "Fashion,Shoes", "Medium", 80, 50, 88, 10, 10, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Minor", "All", 11000),
        ("Book Fair", "Retail", "Books", "Book exhibition and exchange stalls.", "Learning", "Student,Working Professional", "Books,Learning", "Medium", 75, 40, 70, 70, 5, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Minor", "All", 4000),
        ("Fashion Market", "Retail", "Clothing", "Trendy clothes and accessory stalls.", "Engagement", "Student,Working Professional", "Fashion,Shopping", "Large", 78, 48, 82, 10, 10, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 9500),
        ("Plant Market", "Retail", "Gardening", "Stalls for house plants, pots, and soil.", "Relaxation", "Student,Working Professional", "Plants,Nature", "Medium", 72, 40, 70, 20, 20, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Minor", "All", 5000),
        ("Art Market", "Retail", "Art", "Exhibition and sale of resident artwork.", "Creativity", "Student,Working Professional", "Art,Creative", "Medium", 75, 55, 78, 40, 10, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Minor", "All", 5500),
        ("Handmade Crafts", "Retail", "Crafts", "Handmade craft items, candles, and gifts.", "Creativity", "Student,Working Professional", "Art,Crafts", "Medium", 76, 50, 80, 30, 10, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 4500),
        ("Lifestyle Bazaar", "Retail", "Lifestyle", "Pop-up lifestyle products market.", "Engagement", "Student,Working Professional", "Shopping,Social", "Large", 80, 48, 85, 10, 15, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 8500),

        # Entertainment
        ("Live Band", "Entertainment", "Music", "Live performance by local band.", "Fun", "Student,Working Professional", "Music,Entertainment", "Large", 82, 40, 92, 20, 10, "Yes", "Yes", "Yes", "Yes", "Monthly", "Major", "All", 12000),
        ("DJ Night", "Entertainment", "Music", "DJ music performance and dance night.", "Fun", "Student,Working Professional", "Music,Dance", "Large", 85, 30, 95, 10, 20, "Yes", "Yes", "Yes", "Yes", "Monthly", "Major", "All", 10000),
        ("Movie Marathon", "Entertainment", "Screening", "Back-to-back screening of classic movies.", "Relaxation", "Student,Working Professional", "Movies,Entertainment", "Large", 88, 30, 90, 10, 5, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 3000),
        ("Talent Show", "Entertainment", "Performance", "Residents showcase their unique talents.", "Expression", "Student,Working Professional", "Performance,Social", "Medium", 80, 60, 85, 50, 15, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 5000),

        # Community
        ("Quiz League", "Community", "Quiz", "Trivia and quiz league competition.", "Interaction", "Student,Working Professional", "Quiz,Learning", "Medium", 70, 50, 82, 85, 15, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 4000),
        ("Networking Night", "Community", "Networking", "Professional corporate networking night.", "Career", "Working Professional", "Networking,Career", "Medium", 92, 75, 60, 45, 10, "Yes", "Yes", "No", "Yes", "Monthly", "Minor", "All", 6000),
        ("Career Fair", "Community", "Career", "Fair for internships and local hiring.", "Career", "Student,Working Professional", "Career,Jobs", "Large", 85, 90, 50, 50, 10, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 10000),
        ("Wellness Camp", "Community", "Health", "Free general health checkup and wellness advice.", "Wellbeing", "Student,Working Professional", "Health,Fitness", "Medium", 65, 30, 72, 45, 45, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 8000),
        ("Skill Exchange", "Community", "Workshop", "Exchange notes and learn new skills.", "Learning", "Student,Working Professional", "Learning,Skill", "Small", 60, 65, 75, 50, 10, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 3000),
        ("Community Meet-up", "Community", "Social", "Casual chit-chat and meetup.", "Integration", "Student,Working Professional", "Social,Community", "Medium", 75, 35, 70, 90, 5, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 2000),
        ("Cultural Evening", "Community", "Cultural", "Music, dance and cultural evening.", "Cultural exchange", "Student,Working Professional", "Culture,Social", "Large", 78, 60, 85, 80, 20, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 6500),

        # Sports
        ("Pickleball Tournament", "Sports", "Competition", "Outdoor pickleball sports league.", "Engagement", "Student,Working Professional", "Sports,Pickleball", "Medium", 72, 45, 80, 15, 95, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 4500),
        ("Cricket League", "Sports", "Competition", "Inter-property cricket tournament.", "Engagement", "Student,Working Professional", "Cricket,Sports", "Large", 75, 55, 90, 10, 98, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 15000),
        ("Football Screening", "Sports", "Screening", "Live screening of football matches.", "Engagement", "Student,Working Professional", "Football,Sports", "Large", 90, 35, 70, 95, 5, "Yes", "Yes", "Yes", "Yes", "Seasonal", "Major", "All", 5000),
        ("Table Tennis Tournament", "Sports", "Competition", "Indoor table tennis championship.", "Engagement", "Student,Working Professional", "Sports,Competition", "Medium", 65, 50, 82, 85, 90, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Minor", "All", 3000),
        ("Chess Championship", "Sports", "Competition", "Indoor board game chess tournament.", "Engagement", "Student,Working Professional", "Games,Chess", "Medium", 62, 48, 80, 88, 10, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Minor", "All", 2500),
        ("Marathon", "Sports", "Run", "Community run for health awareness.", "Wellbeing", "Student,Working Professional", "Running,Sports", "Large", 70, 30, 85, 10, 95, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 12000),
        ("Cycling Event", "Sports", "Ride", "Weekend community cycling ride.", "Wellbeing", "Student,Working Professional", "Cycling,Sports", "Large", 68, 30, 75, 10, 95, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Major", "All", 6000),

        # Workshops
        ("Photography Workshop", "Workshops", "Learning", "Basics of photography workshop.", "Creativity", "Student,Working Professional", "Photography,Learning", "Medium", 60, 48, 70, 75, 45, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Minor", "All", 4000),
        ("Financial Planning Workshop", "Workshops", "Learning", "Personal tax and wealth management guide.", "Learning", "Working Professional", "Finance,Learning", "Medium", 58, 65, 75, 30, 10, "Yes", "Yes", "No", "Yes", "Quarterly", "Minor", "All", 3500),
        ("Coding Bootcamp", "Workshops", "Learning", "Coding and software build bootcamps.", "Learning", "Student,Working Professional", "Coding,Tech", "Medium", 52, 82, 60, 20, 10, "Yes", "Yes", "Yes", "Yes", "Quarterly", "Minor", "All", 8000),
        ("Yoga Workshop", "Workshops", "Wellness", "Stretches, posture corrections and yoga.", "Wellbeing", "Student,Working Professional", "Yoga,Fitness", "Medium", 62, 32, 70, 35, 80, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 3000),
        ("Mental Wellness Workshop", "Workshops", "Wellness", "Stress buster and mental health session.", "Wellbeing", "Student,Working Professional", "Wellness,Health", "Medium", 60, 30, 70, 30, 20, "Yes", "Yes", "Yes", "Yes", "Monthly", "Minor", "All", 3000)
    ]
    
    rows_added = 0
    ids = df["Event ID"].str.replace("E", "").astype(int).tolist()
    next_id_val = max(ids) + 1
    
    new_rows = []
    for item in new_entries:
        name = item[0]
        if name.strip().lower() in existing_names:
            continue
            
        eid = f"E{next_id_val:03d}"
        next_id_val += 1
        
        new_rows.append({
            "Event ID": eid,
            "Event Name": name,
            "Category": item[1],
            "Subcategory": item[2],
            "Description": item[3],
            "Primary Objective": item[4],
            "Target Occupation": item[5],
            "Target Age Band": "All",
            "Target Tenure Band": "All",
            "Target Interests": item[6],
            "Community Size": item[7],
            "Budget": "Medium",
            "Planning Effort": "Medium",
            "Indoor/Outdoor": "Indoor",
            "Weather Dependency": "No",
            "Expected Attendance %": item[8],
            "Networking Score": item[9],
            "Community Building Score": item[10],
            "Entertainment Score": item[11],
            "Learning Score": item[12],
            "Physical Activity Score": 10,
            "Suitable For New Residents": item[13],
            "Suitable For Long-term Residents": item[14],
            "Suitable For Students": item[15],
            "Suitable For Working Professionals": item[16],
            "Recommended Frequency": item[17],
            "Event Type": item[18],
            "Ideal Community Stage": item[19],
            "Priority": "Medium",
            "Ideal Group Size": "30-80",
            "Maximum Capacity": 100,
            "Event Duration (Hours)": 2,
            "Vendor Required": "No",
            "Equipment Required": "No",
            "Food Included": "No",
            "Repeat Gap (Days)": 30,
            "Suitable Season": "All",
            "Festival Linked": "No",
            "Cost Estimate (₹)": item[20],
            "Community Impact": 8
        })
        rows_added += 1
        
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
        df.to_csv(EVENTS_CSV, index=False)
        print(f"Catalog expanded successfully. Added {rows_added} new events.")
    else:
        print("All events already in catalog.")

if __name__ == "__main__":
    expand()
