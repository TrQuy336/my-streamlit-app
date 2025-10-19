import streamlit as st
from supporter import *
from main_project import export_monthly_report
from PIL import Image


class DataAnalyzer:
    def __init__(self, df):
        self.df = df
        self.chart_folder = "charts"
        self.ensure_folder_exists()

        # Khởi tạo session state
        if "reports" not in st.session_state:
            st.session_state.reports = []
        if "no" not in st.session_state:
            st.session_state.no = 0
        
        
        
        
            
    # hàm kiểm tra file tồn tại hay chưa
    def ensure_folder_exists(self):
        try:
            if not os.path.exists(self.chart_folder):
                os.makedirs(self.chart_folder)
        except Exception as e:
            st.error(f"Lỗi không tìm thấy file: {str(e)}")






    # xác định kiểu dữ liệu
    def prepare_data(self):
        object_cols = self.df.select_dtypes(include="object").columns
        self.df[object_cols] = self.df[object_cols].astype("string")
        self.df.drop_duplicates(inplace=True)

        self.categorical_columns = self.df.select_dtypes(include=["string"]).columns.tolist()
        self.numeric_columns = self.df.select_dtypes(include="number").columns.tolist()






    # hàm chọn và tổng hợp dữ liệu
    def aggregate_data(self):
        category_col = st.selectbox("Chọn cột chữ", self.categorical_columns, key="category")
        numeric_col = st.selectbox("Chọn cột số", self.numeric_columns, key="numeric")

        agg_func = st.selectbox("Chọn hàm tổng hợp", ["sum", "mean", "count", "min", "max"])
        
        if "category" not in st.session_state:
            st.session_state.category = category_col[0]
        
        if "numeric" not in st.session_state:
            st.session_state.numeric = numeric_col[0]

        # Tổng hợp dữ liệu theo lựa chọn
        if agg_func == "sum":
            agg_func = self.df.groupby(category_col)[numeric_col].sum().reset_index()
        elif agg_func == "mean":
            agg_func = self.df.groupby(category_col)[numeric_col].mean().reset_index()
        elif agg_func == "count":
            agg_func = self.df.groupby(category_col)[numeric_col].count().reset_index()
        elif agg_func == "min":
            agg_func = self.df.groupby(category_col)[numeric_col].min().reset_index()
        elif agg_func == "max":
            agg_func = self.df.groupby(category_col)[numeric_col].max().reset_index()
            

        st.subheader(f"Dữ liệu {agg_func} của {numeric_col} theo {category_col}")
        st.dataframe(agg_func.style.background_gradient(cmap="coolwarm"))

        return agg_func, category_col, numeric_col






    # hàm vẽ biểu đồ và lưu
    def plot_and_save_chart(self, aggregated_data, category_col, numeric_col):
        chart_type = st.selectbox("Chọn loại biểu đồ", ["Line Chart", "Bar Chart", "Scatter Plot", "Pie Chart"])

        if st.button("Plot Chart"):
            chart_path, chart_name = plot_chart(self.chart_folder, chart_type, aggregated_data, category_col, numeric_col)
            response = generate_report_from_chart(self.chart_folder, chart_name)

            report = {
                "pivot_table": aggregated_data,
                "chart_path": chart_path,
                "sheet_name": f"Sheet {st.session_state.no}",
                "insight": response
            }

            st.session_state.reports.append(report)
            st.session_state.no += 1
            st.success("Biểu đồ đã được tạo và lưu thành công!")
            
            
          # thêm nút xuất báo cáo  
        if st.button("Xuất file excel tổng hợp"):
            export_monthly_report()   
            
            
            
            
            
            
    # hiển thị biểu đồ
    def show_reports(self):

        for i, report in enumerate(st.session_state.reports):
            filename = report["chart_path"]
            if filename.endswith((".png", ".jpg", ".jpeg")):
                file_path = os.path.join(self.chart_folder, filename)
                if os.path.exists(file_path):
                    image = Image.open(file_path)
                    st.image(image, caption=filename, use_column_width=True)

                    if st.button(f"Remove chart {i+1}", key=f"remove_{i}"):
                        remove_chart(file_path)
                        st.session_state.reports.pop(i)
                        st.rerun()
                        
                        

    # hàm chạy
    def run(self):
        self.prepare_data()
        aggregated_data, cat_col, num_col = self.aggregate_data()
        self.plot_and_save_chart(aggregated_data, cat_col, num_col)
        self.show_reports()                
