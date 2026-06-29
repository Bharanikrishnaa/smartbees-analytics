import anthropic
import pandas as pd
import os

# Load CSV
df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'marketing_data.csv'))

# Summary metrics
total_revenue = df['revenue'].sum()
total_conversions = df['conversions'].sum()
best_channel = df.groupby('channel')['revenue'].sum().idxmax()
avg_roas = df[df['roas'] > 0]['roas'].mean()

# Build prompt
prompt = f"""
Tu es un analyste marketing senior. Voici les données de performance 
marketing des 90 derniers jours :

- Revenu total : {total_revenue:.2f}€
- Conversions totales : {total_conversions}
- Meilleur canal par revenu : {best_channel}
- ROAS moyen (canaux payants) : {avg_roas:.2f}

Rédige un rapport d'analyse concis en français avec :
1. Performance globale
2. Points forts
3. Points d'attention
4. Recommandations
"""

# Call Claude API - key loaded from environment
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    messages=[{"role": "user", "content": prompt}]
)

print(response.content[0].text)