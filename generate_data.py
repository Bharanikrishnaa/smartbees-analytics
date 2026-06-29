import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Reproducible output every time
np.random.seed(42)

# 1. Date range — last 90 days ending today
end_date = datetime(2026, 6, 17)
dates = [end_date - timedelta(days=i) for i in range(90)]
dates.reverse()

# 2. Channels
channels = ['paid_search', 'organic', 'paid_social', 'email', 'direct']

# 3. Generate rows
rows = []

for date in dates:
    for channel in channels:

        # Sessions
        if channel == 'paid_search':
            sessions = int(np.random.normal(4000, 400))
        elif channel == 'organic':
            sessions = int(np.random.normal(2000, 300))
        elif channel == 'paid_social':
            sessions = int(np.random.normal(1500, 200))
        elif channel == 'email':
            sessions = int(np.random.normal(800, 100))
        else:
            sessions = int(np.random.normal(600, 80))

        # Protect against negative sessions
        sessions = max(sessions, 0)

        # Conversions
        conversion_rate = np.random.uniform(0.02, 0.06)
        conversions = int(sessions * conversion_rate)

        # Revenue
        aov = np.random.uniform(45, 80)
        revenue = round(conversions * aov, 2)

        # Ad spend — only paid channels
        if channel in ['paid_search', 'paid_social']:
            ad_spend = round(np.random.uniform(500, 1500), 2)
        else:
            ad_spend = 0

        # CAC and ROAS
        cac = round(ad_spend / conversions, 2) if conversions > 0 and ad_spend > 0 else 0
        roas = round(revenue / ad_spend, 2) if ad_spend > 0 else 0

        rows.append([
            date.strftime('%Y-%m-%d'),
            channel,
            sessions,
            conversions,
            revenue,
            ad_spend,
            cac,
            roas
        ])

# 4. Convert to DataFrame
df = pd.DataFrame(rows, columns=[
    'date', 'channel', 'sessions',
    'conversions', 'revenue', 'ad_spend', 'cac', 'roas'
])

# 5. Save using relative path
output_path = os.path.join(os.path.dirname(__file__), 'marketing_data.csv')
df.to_csv(output_path, index=False)
print(f"Done! {len(df)} rows saved to {output_path}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Total revenue: €{df['revenue'].sum():,.2f}")