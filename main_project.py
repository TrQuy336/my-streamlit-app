import pandas as pd
import streamlit as st
import os
from supporter import *
from class_supporter import *
import openpyxl 
from gemini_rag import *
from PIL import Image

# xuất file tổng hợp
def export_monthly_report():
    if "reports" not in st.session_state or len(st.session_state.reports) == 0:
        st.warning("Chưa có biểu đồ hoặc dữ liệu để xuất thông tin")
        return
    save_path = "report_monthly.xlsx"
    with pd.ExcelWriter(save_path, engine="openpyxl") as writer:
        for report in st.session_state.reports:
            sheet_name = report["sheet_name"]
            df_report = report["pivot_table"]
            df_report.to_excel(writer, sheet_name=sheet_name, index=False)
            
            if report.get("insight"):
                insight_df = pd.DataFrame({f"Phân tích / Nhận xét": [report["insight"]]})
                start_row = len(df_report) + 3
                insight_df.to_excel(writer, sheet_name=sheet_name,startrow=start_row, index=False)
    st.success(f"Đã xuất file excel {save_path} thành công")
    with open(save_path, "rb") as f:
        st.download_button("Tải file excel tổng hợp", f, file_name="report_monthly.xlsx")
        
        
        

# check datetime
def is_date_str( s):
    try:
        pd.to_datetime(s)
        return True
    except:
        return False




# chuyển tháng thành mùa
def month_to_season(month):
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    elif month in [9, 10, 11]:
        return "Fall"
    else:
        return "Unknown"





# xử lý cột season
def handle_season(df):
    if "Season" not in df.columns:
        df["Season"] = None
    mask_date = df["Season"].apply(lambda x: pd.notnull(x) and is_date_str(x))

    if mask_date.any():
        df.loc[mask_date, "Season"] = pd.to_datetime(df.loc[mask_date, "Season"]).dt.month.apply(month_to_season)

    if df["Season"].isnull().sum() > 0:
        if "Month" in df.columns:
            df["Season"] = df["Season"].fillna(df["Month"].apply(month_to_season))
        else:
            df["Season"] = df["Season"].fillna("Unknown")






# fill null tự động
def auto_fill_nulls(df):
        for col in df.columns:
            if df[col].dtype in [float, int]:
                if df[col].isnull().sum() > 0:
                    df[col] = df[col].fillna(df[col].mean())
            else:
                if df[col].isnull().sum() > 0:
                    df[col] = df[col].fillna(df[col].mode()[0])
        st.success("File sau khi đã xử lý")





# TAB!: Data Analysis
def tab_data_analysis():
    
    
    # đặt giá trị mặc định ban đầu
    if "processed_file" not in st.session_state:
        st.session_state.processed_file = False
    if "df" not in st.session_state:
        st.session_state.df = None
    if "show_aggregate" not in st.session_state:
        st.session_state.show_aggregate = False
    
    
    modes = st.radio("Chọn file để xử lý", ["File nội bộ", "upload files"])
    if modes == "File nội bộ":
        try:
            with st.spinner("Đang xử lý tài liệu..."):
                df = pd.read_csv("https://raw.githubusercontent.com/riodev1310/rio_datasets/refs/heads/main/preprocessing_data.csv")
                st.success("Tải file nội bộ thành công")
                st.dataframe(df)
                
                auto_fill_nulls(df)
                handle_season(df)
                st.dataframe(df)
                return df
        except Exception as e:
            st.error(f"Lỗi khi xử lý file nội bộ: {e}")
            return None
    elif modes == "upload files":
        upload_file = st.file_uploader("Tải lên file CSV", type=["csv"])
        if upload_file is not None:
            try:
                df = pd.read_csv(upload_file)
                st.success("Đã tải file lên")
                st.dataframe(df)
                st.session_state.df = df
            except Exception as e:
                st.error(f"Lỗi khi đọc file: {e}")
                return None
        else:
            st.warning("Vui lòng tải lên file CSV để xử lý")
            return None
        
        
    # nếu thông tin được load thì null sẽ được xử lý
    if st.session_state.df is not None:
        df = st.session_state.df.copy()
        st.subheader("Xử lý giá trị null")
        null_handling_mode = st.radio("Chọn phương pháp xử lý null", ["Tự động", "Thủ công"])
        if null_handling_mode == "Tự động":
            if st.button("Xử lý null tự động"):
                with st.spinner("Đang xử lý giá trị null tự động..."):
                    auto_fill_nulls(df)
                    handle_season(df)
                    st.dataframe(df)
                    st.session_state.df = df
                    st.session_state.null_processed = True
                    st.success("Đã xử lý null tự động và cập nhật cột Season")
        elif null_handling_mode == "Thủ công":
            columns_to_nulls = st.multiselect("Chọn cột cần xử lý", df.columns)
            if columns_to_nulls:
                method = st.selectbox(
                    "Chọn phương pháp điền null",
                    ["Trung bình (mean)", "Trung vị (median)", "Mode", "Giá trị cụ thể"]
                )

                if st.button("Xử lý Null thủ công"):
                    with st.spinner("Đang xử lý giá trị null thủ công..."):
                        for col in columns_to_nulls:
                            if method == "Trung bình (mean)" and df[col].dtype in [float, int]:
                                df[col] = df[col].fillna(df[col].mean())
                            elif method == "Trung vị (median)" and df[col].dtype in [float, int]:
                                df[col] = df[col].fillna(df[col].median())
                            elif method == "Mode":
                                df[col] = df[col].fillna(df[col].mode()[0])
                            elif method == "Giá trị cụ thể":
                                fill_value = st.text_input(f"Nhập giá trị để điền cho {col}", "0")
                                try:
                                    fill_value = float(fill_value) if fill_value.replace(".", "").isdigit() else fill_value
                                    df[col] = df[col].fillna(fill_value)
                                except:
                                    st.error("Giá trị không hợp lệ")
                                    return None         
                        # Gọi xử lý Season
                        handle_season(df)
                        st.success("File sau khi đã xử lý")
                        st.session_state.null_processed = True
                        st.success("Đã xử lý Null thủ công thành công")
                        st.dataframe(df)
                        
            else:
                st.info("Vui lòng chọn ít nhất một cột để xử lý null")




            # Sau khi xử lý Null xong 
        if st.session_state.get("null_processed", False):
            st.divider()
            st.subheader("Tổng hợp & Vẽ biểu đồ")
            
            if st.button("Tổng hợp dữ liệu"):
                st.session_state.show_analysis = True
                
            if st.session_state.get("show_analysis", False):
                analyzer = DataAnalyzer(st.session_state.df)
                analyzer.run()
    
    # nút reset
    if st.button("Reset tab Data Analysis"):
        st.session_state.clear()









# TAB 2: Mapping Data
def tab_mapping_data():
    upload_files = st.file_uploader("Tải lên file excel", type=["xlsx"])
    if upload_files is None:
        st.warning("Vui lòng tải dữ liệu files Excel để xử lý")
    else:
        with st.spinner("Đang xử lý tài liệu..."):
            df = pd.read_excel(upload_files, engine="openpyxl")
            st.success("Upload file successfully")
            st.dataframe(df)

            # chọn 2 cột để tạo cột mới
            all_columns = df.columns.tolist()
            col_1 = st.selectbox("Chọn cột thứ nhất (ví dụ: Doanh thu)", all_columns, key="col_1")
            col_2 = st.selectbox("Chọn cột thứ hai (ví dụ: Chi phí)", all_columns, key="col_2")

            # nhập tên cột mới
            new_col_name = st.text_input("Nhập tên cột mới (ví dụ: Lợi nhuận)", key="new_col")

            # chọn phép tính
            operation = st.selectbox(
                "Chọn phép tính giữa hai cột",
                ["Trừ (-)", "Cộng (+)", "Nhân (*)", "Chia (/)"]
            )

            if st.button("Tạo cột mới"):
                try:
                    if new_col_name.strip() == "":
                        st.warning("Vui lòng nhập tên cột mới")
                    else:
                        # xử lý phép tính
                        if operation == "Trừ (-)":
                            df[new_col_name] = df[col_1] - df[col_2]
                        elif operation == "Cộng (+)":
                            df[new_col_name] = df[col_1] + df[col_2]
                        elif operation == "Nhân (*)":
                            df[new_col_name] = df[col_1] * df[col_2]
                        elif operation == "Chia (/)":
                            df[new_col_name] = df[col_1] / df[col_2]

                        st.success(f"Đã thêm cột '{new_col_name}' vào dữ liệu")
                        st.dataframe(df)

                        # xuất ra file excel mới
                        output_path = "mapping_data.xlsx"
                        df.to_excel(output_path, index=False)
                        st.success(f"Đã lưu kết quả vào file {output_path}")

                        with open(output_path, "rb") as f:
                            st.download_button(
                                label="Tải file Excel đã cập nhật",
                                data=f,
                                file_name=output_path
                            )
                except Exception as e:
                    st.error(f"Lỗi khi xử lý: {e}")
                    
    if st.button("Reset tab Mapping Data"):
        st.session_state.clear()








# TAB 3: Gemini Rag
def tab_gemini_rag():
    bot = PDFChatBot()
    bot.run()
    if st.button("Reset tab Gemini Rag"):
        st.session_state.clear()







# hàm chính
def main():
    st.set_page_config(page_title="Data Cleaning App", layout="wide")
    st.title("Data Preprocessing — Truong Quy")
    
    # Tạo Tabs
    tab1, tab2, tab3 = st.tabs(["Data Analysis", "Mapping Data", "Gemini RAG"])


    df = None
    with tab1:
        df = tab_data_analysis()
        if df is not None:
            analyzer = DataAnalyzer(df)
            analyzer.run()


    with tab2:
        tab_mapping_data()

    with tab3:
        tab_gemini_rag()




if __name__ == "__main__":
    main()
