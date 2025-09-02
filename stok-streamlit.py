import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from google import genai
import json

load_dotenv()

#database
config ={

        'host': os.getenv("DB_HOST"),
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASS"),
        'database': os.getenv("DB_NAME"),
        'port': int(os.getenv("DB_PORT"))
    }


try:
    # Build SQLAlchemy connection string
    connection_string = (
        f"mysql+mysqlconnector://{config['user']}:{config['password']}@"
        f"{config['host']}:{config['port']}/{config['database']}"
    )
    engine = create_engine(connection_string)
   
    query2 = "SELECT * FROM beli"

except Exception as e:
    print("❌ Error:", e)
    st.stop()


#TOP
st.set_page_config(
    page_title="SALES DASHBOARD",
    page_icon=":bar_chart:",
    layout="wide"
)
#tabel stok
# Ambil data pembelian per KODE dari tabel beli
beli_in_df = pd.read_sql_query("""
SELECT 
    KODE,
    SUM(JUMLAH) AS BARANG_IN
FROM beli
GROUP BY KODE                               
""", engine)


# Ambil data penjualan per KODE dari tabel jual
jual_out_df = pd.read_sql_query("""
SELECT 
    KODE,
    SUM(JUMLAH) AS BARANG_OUT
FROM jual
GROUP BY KODE
ORDER BY BARANG_OUT DESC
""", engine)

stok_df = pd.read_sql_query("""
SELECT 
    KODE,
    NAMABRG,
    SATUAN,
    JUMLAH,
    -- SISA_1 = JUMLAH stok - JUMLAH jual_out + JUMLAH beli_in
    (JUMLAH 
     - COALESCE((SELECT SUM(JUMLAH) FROM jual WHERE jual.KODE = stok.KODE), 0)
     + COALESCE((SELECT SUM(JUMLAH) FROM beli WHERE beli.KODE = stok.KODE), 0)
    ) AS SISA_1
FROM stok AS stok
""", engine)

# Gabungkan BARANG_OUT dari jual_out_df ke stok_df berdasarkan KODE
stok_df = stok_df.merge(jual_out_df, on="KODE", how="left")

# Gabungkan BAANG_IN dari beli_in_df ke stok_df berdasarkan KODE
stok_df = stok_df.merge(beli_in_df, on="KODE", how="left")

# Sekarang stok_df memiliki kolom BARANG_IN yang nilainya dari JUMLAH beli_in


#tabel penjualan
total_jual_perkode = """
SELECT 
    KODE,
    NAMABRG,
    SATUAN,
    SUM(JUMLAH) AS JUMLAH,
    SUM(TOTAL) AS TOTAL,
    SUM(DISC) AS DISC
FROM jual
GROUP BY KODE
ORDER BY TOTAL DESC
"""

jual_filter = """
SELECT 
    DATE(TGL) AS TGL,
    SUM(JUMLAH) AS JUMLAH,
    SUM(TOTAL) AS TOTAL,
    SUM(DISC) AS DISC
FROM jual
GROUP BY DATE(TGL)
ORDER BY TGL
"""

beli_filter = """
SELECT 
    TGL,
    KODE,
    NAMABRG,
    SATUAN,
    JUMLAH
    FROM beli
"""
 


#MAIN PAGE
st.title(":bar_chart: SALES DASHBOARD")
st.markdown("####")
st.sidebar.write("✅ Koneksi berhasil!")

# Set the title and a caption for the web page
st.markdown("####")
st.title("💬 Gemini Chatbot untuk pencarian Stok")
st.caption("Tuliskan nama Barang yang ingin Anda Cari")
st.write("STOK (Top 20 Rows):")
st.dataframe(stok_df.head(20))

rekap_dataset1 = pd.read_sql_query(total_jual_perkode, engine)
st.write("Penjualan Tertinggi (Top 20 Rows):")
st.dataframe(rekap_dataset1.head(20))

dataset1 = pd.read_sql_query(jual_filter, engine)
st.write("Penjualan per periode (Top 20 Rows):")
st.dataframe(dataset1.head(20))

dataset2 = pd.read_sql_query(beli_filter, engine)
st.write("Pembelian (Top 20 Rows):")
st.dataframe(dataset2.head(20))


dataset2["TGL"] = pd.to_datetime(dataset2["TGL"])
df2 = dataset2.groupby(by=dataset2.TGL.dt.month).JUMLAH.sum()

dataset1 = pd.read_sql_query(jual_filter, engine)
dataset1["TGL"] = pd.to_datetime(dataset1["TGL"])
df = dataset1.groupby(by=dataset1.TGL.dt.month).TOTAL.sum()

#SIDEBAR

#penjualan

st.sidebar.header("FILTER DATA:")
st.sidebar.write("PENJUALAN")


bulan_options = sorted(dataset1["TGL"].dt.month.unique())
tgl = st.sidebar.multiselect(
    "Pilih Bulan",
    options=bulan_options,
    default=bulan_options
)

df["TGL"]=dataset1["TGL"].dt.month
df_selection=df.to_frame()
df_selection = df_selection.query("TGL==@tgl")

#pembelian
st.sidebar.header("PEMBELIAN")

bulan1_options = sorted(dataset2["TGL"].dt.month.unique())
tgl_beli = st.sidebar.multiselect(
    "Pilih Bulan",
    options=bulan1_options,
    default=bulan1_options
)

df2["TGL"]=dataset2["TGL"].dt.month
df2_selection=df2.to_frame()
df2_selection = df2_selection.query("TGL==@tgl_beli")




#TOP KPI's
total_sales = df_selection["TOTAL"].sum()
#total_order =df2_selection["Nilai"].sum() 
#gross_profit = total_sales-total_order

top_col1 ,top_col2, top_profit =st.columns(3)
with top_col1:
    st.subheader("Total penjualan:")
    st.subheader(f"Rp. {total_sales:,}")
with top_col2:
    st.subheader("Total pembelian:")
    #st.subheader(f"Rp. {total_order:,}")
with top_profit:
    st.subheader("Profit:")
    #st.subheader(f"Rp. {gross_profit:,}") 

st.markdown("---")

#Sub KPI
col1, col2,col3,col4 =st.columns(4)
with col1:
    st.markdown("##### penjualan:")
    st.dataframe(df_selection)
with col2:
    st.markdown("##### Grafik:") 
    sales_grafik = (dataset1.groupby(by=dataset1.TGL.dt.month).TOTAL.sum())
    fig_sales_grafik = px.bar(
        sales_grafik,
        x=sales_grafik.index,
        y="TOTAL",
        orientation="h",
        title="<b>penjualan th berjalan</b>",
        color_discrete_sequence=["#0083B8"]*len(sales_grafik),
        template="plotly_white",
        )
    st.plotly_chart(fig_sales_grafik)

st.markdown("---")

col2_1, col2_2,col2_3,col2_4 =st.columns(4)
with col2_1:    
        st.markdown("##### Pembelian:")
        st.dataframe(df2_selection) 
with col2_2:
    order_grafik = (dataset2.groupby(by=dataset2.TGL.dt.month).JUMLAH.sum())

    fig_order_grafik = px.area(
         order_grafik,
         x=order_grafik.index,
         y="JUMLAH",
         orientation="v",
         title="<b>Pembelian th berjalan</b>",
         color_discrete_sequence=["#0083B8"]*len(order_grafik),
         template="plotly_white",
        )
    st.plotly_chart(fig_order_grafik)

#stok
st.sidebar.header("PENCARIAN STOK")

# --- 2. Sidebar for Settings ---

# Create a sidebar section for app settings using 'with st.sidebar:'
with st.sidebar:
    # Add a subheader to organize the settings
    st.subheader("Masukan API key Anda")
    
    # Create a text input field for the Google AI API Key.
    # 'type="password"' hides the key as the user types it.
    google_api_key = st.text_input("Google AI API Key", type="password")
    
    # Create a button to reset the conversation.
    # 'help' provides a tooltip that appears when hovering over the button.
    reset_button = st.button("Reset Conversation", help="Clear all messages and start fresh")

# --- 3. API Key and Client Initialization ---

# Check if the user has provided an API key.
# If not, display an informational message and stop the app from running further.
if not google_api_key:
    st.info("Silakan isi Google AI API key pada sidebar untuk mulai mencari Barang tertentu.", icon="🗝️")
    st.stop()

if ("genai_client" not in st.session_state) or (getattr(st.session_state, "_last_key", None) != google_api_key):
    try:
        # If the conditions are met, create a new client.
        st.session_state.genai_client = genai.Client(api_key=google_api_key)
        # Store the new key in session state to compare against later.
        st.session_state._last_key = google_api_key
        # Since the key changed, we must clear the old chat and message history.
        # .pop() safely removes an item from session_state.
        st.session_state.pop("chat", None)
        st.session_state.pop("messages", None)
    except Exception as e:
        # If the key is invalid, show an error and stop.
        st.error(f"Invalid API Key: {e}")
        st.stop()


# --- 4. Chat History Management ---

# Initialize the chat session if it doesn't already exist in memory.
if "chat" not in st.session_state:
    # Create a new chat instance using the 'gemini-2.5-flash' model.
    st.session_state.chat = st.session_state.genai_client.chats.create(model="gemini-2.5-flash")

# Initialize the message history (as a list) if it doesn't exist.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Handle the reset button click.
if reset_button:
    # If the reset button is clicked, clear the chat object and message history from memory.
    st.session_state.pop("chat", None)
    st.session_state.pop("messages", None)
    # st.rerun() tells Streamlit to refresh the page from the top.
    st.rerun()

# --- 5. Display Past Messages ---

# Loop through every message currently stored in the session state.
for msg in st.session_state.messages:
    # For each message, create a chat message bubble with the appropriate role ("user" or "assistant").
    with st.chat_message(msg["role"]):
        # Display the content of the message using Markdown for nice formatting.
        st.markdown(msg["content"])

# --- 6. Handle User Input and API Communication ---

# Create a chat input box at the bottom of the page.
# The user's typed message will be stored in the 'prompt' variable.
prompt = st.chat_input("Masukan nama barang yang ingin Anda cari di sini...")

# Check if the user has entered a message.
if prompt:
    # 1. Add the user's message to our message history list.
    st.session_state.messages.append({"role": "user", "content": prompt})
    # 2. Display the user's message on the screen immediately for a responsive feel.
    with st.chat_message("user"):
        st.markdown(prompt)
    promp1=prompt
    # 3. Get the assistant's response.
    # Use a 'try...except' block to gracefully handle potential errors (e.g., network issues, API errors).
    try:
     # Ambil data pembelian per KODE dari tabel beli
        prompt = prompt + """tolong jawab dengan hasil query stok dari database yang sudah dideklarasikan di atas saja,
          dalam format tabel yang rapi dan mudah dibaca jika ada jawabn lain gunakan bahasa yang sama dengan penanya:"""
        # Send the user's prompt to the Gemini API.
        response = st.session_state.chat.send_message(prompt)
        
        # Safely get the text from the response object.
        # `hasattr(object, 'attribute_name')` checks if an object has a specific property.
        # This prevents an error if the API response object doesn't have a '.text' attribute.
        if hasattr(response, "text"):
            answer = response.text
        else:
            # If there's no '.text', convert the whole response to a string as a fallback.
            answer = str(response)

    except Exception as e:
        # If any error occurs, create an error message to display to the user.
        answer = f"An error occurred: {e}"

    # 4. Display the assistant's response.
    with st.chat_message("assistant"):
        st.markdown(answer)
    # 5. Add the assistant's response to the message history list.
    st.session_state.messages.append({"role": "assistant", "content": answer})

    beli_in_df1 = pd.read_sql_query("""
    SELECT 
    KODE,
    SUM(JUMLAH) AS BARANG_IN 
    FROM beli
    GROUP BY KODE                               
    """, engine)


    # Ambil data penjualan per KODE dari tabel jual
    jual_out_df1 = pd.read_sql_query("""
    SELECT 
    KODE,
    SUM(JUMLAH) AS BARANG_OUT
    FROM jual
    GROUP BY KODE 
    ORDER BY BARANG_OUT DESC
    """, engine)
    
    stok_df1 = pd.read_sql_query("""
    SELECT 
    KODE,
    NAMABRG,
    SATUAN,
    JUMLAH,
    -- SISA_1 = JUMLAH stok - JUMLAH jual_out + JUMLAH beli_in
    (JUMLAH 
     - COALESCE((SELECT SUM(JUMLAH) FROM jual WHERE jual.KODE = stok.KODE), 0)
     + COALESCE((SELECT SUM(JUMLAH) FROM beli WHERE beli.KODE = stok.KODE), 0)
    ) AS SISA_1
    FROM stok AS stok
    where NAMABRG like '%"""+promp1+"""%'                                  
    """, engine)

    # Gabungkan BARANG_OUT dari jual_out_df ke stok_df berdasarkan KODE
    stok_df1 = stok_df1.merge(jual_out_df1, on="KODE", how="left")

# Gabungkan BAANG_IN dari beli_in_df ke stok_df berdasarkan KODE
stok_df1 = stok_df1.merge(beli_in_df1, on="KODE", how="left")

     #prompt = stok_df1.to_string()
     
st.write("STOK (Top 20):")
st.dataframe(stok_df1.head(20))
        
    
#Style
dashbd_style="""
        <style>
        #MainMenu {visibility : hidden;}
        footer {visibility : hidden;}
        header {visibility : hidden;}
        </style>
        """

st.markdown(dashbd_style, unsafe_allow_html=True)
