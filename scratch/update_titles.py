import asyncio
import sqlite3

def update_db():
    conn = sqlite3.connect("data/discovery_pulse.db")
    cursor = conn.cursor()
    
    # Try to add the column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE phase4_opportunity_areas ADD COLUMN original_generated_label VARCHAR")
    except sqlite3.OperationalError:
        pass # Column might already exist
        
    mapping = {
        "Marketplace Quality & Price Governance": "Shoppers experience unexpected pricing changes, manipulative sale mechanics, and non-refundable platform fees, which undermines platform trust.",
        "Hyper-Personalized Fit & Sizing Intelligence": "High-intent shoppers experience fit uncertainty and lack sufficient information to judge whether apparel will fit as expected before committing to purchase.",
        "Frictionless Post-Purchase Operations & Support": "Past delivery delays, difficult return processes, and unsupportive customer care create friction that may reduce confidence in future purchases."
    }
    
    for old_title, new_title in mapping.items():
        # First check if original_generated_label is empty, if so, populate it with old_title
        cursor.execute("UPDATE phase4_opportunity_areas SET original_generated_label = ? WHERE title = ?", (old_title, old_title))
        # Then update title
        cursor.execute("UPDATE phase4_opportunity_areas SET title = ? WHERE title = ?", (new_title, old_title))
        
    conn.commit()
    
    cursor.execute("SELECT title, original_generated_label FROM phase4_opportunity_areas")
    print(cursor.fetchall())
    
    conn.close()

if __name__ == "__main__":
    update_db()
