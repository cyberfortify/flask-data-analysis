from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import chardet  

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)
            return redirect(url_for("analyze", filename=file.filename))
    return render_template("index.html")

@app.route("/analyze/<filename>", methods=["GET", "POST"])
def analyze(filename):
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    # Detect file extension
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext == ".csv":
            # Auto-detect encoding
            with open(filepath, "rb") as f:
                result = chardet.detect(f.read(100000))  # Read first 100KB
                encoding_type = result["encoding"]

            df = pd.read_csv(filepath, encoding=encoding_type)  # FIXED: Removed `errors="replace"`
        elif ext in [".xls", ".xlsx"]:
            df = pd.read_excel(filepath, engine="openpyxl")  
        else:
            return "Unsupported file format", 400  
    except Exception as e:
        return f"Error reading file: {str(e)}", 400 

    # Count missing values
    missing_values = df.isnull().sum().to_frame(name="Missing Values")

    # Convert tables to HTML
    preview = df.head().to_html(classes="table table-striped")
    describe = df.describe().to_html(classes="table table-bordered")
    missing_values_html = missing_values.to_html(classes="table table-warning")

    sorted_data = None
    filtered_data = None
    grouped_data = None

    if request.method == "POST":
        action = request.form.get("action")
        column = request.form.get("column")

        if action == "drop":  
            df = df.dropna()
        elif action == "fill":  
            df = df.fillna(df.mean(numeric_only=True))
        elif action == "sort" and column in df.columns:
            df = df.sort_values(by=column)
            sorted_data = df.head().to_html(classes="table table-success")
        elif action == "filter" and column in df.columns:
            threshold = request.form.get("threshold", type=float)
            df = df[df[column] > threshold]
            filtered_data = df.head().to_html(classes="table table-info")
        elif action == "group" and column in df.columns:
            grouped = df.groupby(column).mean(numeric_only=True)
            grouped_data = grouped.to_html(classes="table table-dark")

        df.to_csv(filepath, index=False)
        return redirect(url_for("analyze", filename=filename))
    
    # Save cleaned data and pass `processed_file` for download
    cleaned_filename = "cleaned_" + filename
    cleaned_filepath = os.path.join(app.config["UPLOAD_FOLDER"], cleaned_filename)
    df.to_csv(cleaned_filepath, index=False)

    return render_template("analyze.html", 
                           filename=filename, 
                           processed_file=cleaned_filename,  # ✅ Pass processed file
                           preview=preview, 
                           describe=describe, 
                           missing_values=missing_values_html,
                           sorted_data=sorted_data, 
                           filtered_data=filtered_data,
                           grouped_data=grouped_data, 
                           columns=df.columns.tolist())

    
    
@app.route("/visualize/<filename>", methods=["GET", "POST"])
def visualize(filename):
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    df = pd.read_csv(filepath)  # Read CSV file

    plot_url = None
    if request.method == "POST":
        plot_type = request.form.get("plot_type")
        column_x = request.form.get("column_x")
        column_y = request.form.get("column_y")

        plt.figure(figsize=(8,5))  # Set figure size

        if plot_type == "bar" and column_x and column_y:
            sns.barplot(x=df[column_x], y=df[column_y])
        elif plot_type == "line" and column_x and column_y:
            sns.lineplot(x=df[column_x], y=df[column_y])
        elif plot_type == "hist" and column_x:
            sns.histplot(df[column_x], bins=20)
        elif plot_type == "heatmap":
            sns.heatmap(df.corr(), annot=True, cmap="coolwarm")

        plt.xticks(rotation=45)  # Rotate x-axis labels
        plt.tight_layout()

        # Save the plot
        plot_path = os.path.join("static", "plot.png")
        plt.savefig(plot_path)
        plot_url = "/" + plot_path  # Store URL for display

    return render_template("visualize.html", filename=filename, columns=df.columns.tolist(), plot_url=plot_url)


@app.route("/download/<filename>")
def download_file(filename):
    """ Serve the processed file for download """
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
