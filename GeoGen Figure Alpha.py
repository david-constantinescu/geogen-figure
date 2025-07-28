import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
import re
import subprocess
import os
import sys
from google import genai
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile
import platform
from pathlib import Path
import queue
import numpy as np
import unicodedata


# Global queues for thread communication
drawing_queue = queue.Queue()
solution_queue = queue.Queue()


#You can obtain a key from Google AI Studio, this is used for generating the drawing and the solution.
# Config keys, you can get your own free gemini key at 
GEMINI_API_KEY = "your_key_goes_here"
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
TEMP_DIR = tempfile.gettempdir()
OUTPUT_FILE = os.path.join(TEMP_DIR, "generated_drawing.py")



def get_system_font():
    """Get the best available system font"""
    system = platform.system()
    if system == 'Darwin':
        fonts = [
            '/System/Library/Fonts/SF-Pro-Display-Regular.otf',
            '/System/Library/Fonts/Helvetica.ttc',
            '/Library/Fonts/Arial Unicode.ttf'
        ]
    elif system == 'Linux':
        fonts = ['/System/Library/Fonts/SF-Pro-Display-Regular.otf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    else:  # Windows
        fonts = ['C:\\Windows\\Fonts\\SF-Pro-Display-Regular.otf', 'C:\\Windows\\Fonts\\arial.ttf']
        
    for font in fonts:
        if os.path.exists(font):
            try:
                pdfmetrics.registerFont(TTFont('SystemFont', font))
                return 'SystemFont'
            except:
                continue
    return 'Helvetica'

PDF_FONT = get_system_font()

def extract_python_code(response_text):
    """Extract Python code from response"""
    match = re.search(r"```python(.*?)```", response_text, re.DOTALL)
    return match.group(1).strip() if match else response_text.strip()

def execute_drawing():
    """Execute the drawing code"""
    try:
        while True:
            try:
                python_code = drawing_queue.get_nowait()
                plt.close('all')  # Ensure all figures are closed first
                local_namespace = {'plt': plt, 'np': np}
                exec(python_code, local_namespace)
                # Fix deprecated or missing 3D axis attributes for compatibility
                from mpl_toolkits.mplot3d import Axes3D
                for fig_num in plt.get_fignums():
                    fig = plt.figure(fig_num)
                    for ax in fig.get_axes():
                        if isinstance(ax, Axes3D):
                            # These were used in older matplotlib for manual axis tweaks
                            if hasattr(ax, 'w_xaxis'):
                                ax.xaxis = ax.w_xaxis
                            if hasattr(ax, 'w_yaxis'):
                                ax.yaxis = ax.w_yaxis
                            if hasattr(ax, 'w_zaxis'):
                                ax.zaxis = ax.w_zaxis
                figs = [plt.figure(i) for i in plt.get_fignums()]
                if figs:
                    manager = figs[-1].canvas.manager
                    toolbar = manager.toolbar

                    def print_figure():
                        temp_pdf = os.path.join(TEMP_DIR, "temp_print.pdf")
                        plt.savefig(temp_pdf, bbox_inches='tight', dpi=300)
                        try:
                            if platform.system() == 'Darwin':
                                subprocess.run(['lpr', temp_pdf])
                            elif platform.system() == 'Linux':
                                subprocess.run(['lpr', temp_pdf])
                            else:
                                os.startfile(temp_pdf, 'print')
                        finally:
                            try:
                                os.remove(temp_pdf)
                            except:
                                pass

                    if hasattr(toolbar, 'toolitems'):
                        toolbar.toolitems = list(toolbar.toolitems) + [
                            ('Print', 'Print the figure', 'print', 'print_figure')
                        ]
                        toolbar.print_figure = print_figure

                plt.show(block=False)
                drawing_queue.task_done()

            except queue.Empty:
                break
            except Exception as e:
                messagebox.showerror("Error", f"Drawing execution failed: {str(e)}")
                drawing_queue.task_done()
    except Exception as e:
        messagebox.showerror("Error", f"Drawing system error: {str(e)}")
    return True

def generate_geometry(hypothesis):
    """Generate geometric drawing"""
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-pro",
            contents=f"""
            Based on the following geometrical hypothesis, please send me a Python script that can generate a drawing of the hypothesis, and only that.
            The script should use matplotlib to create the drawing.
            Please keep it accurate and send me back just the Python code. You are strictly prohibited from including any explanations, details, or instructions—just the Python code.
            Please make sure that a grid is not shown. Do not answer the question or think about its solution, just provide the Python code for the drawing.
            The drawing should be dark grey on a white background, with black point labels.
            Ensure every point is labeled next to its position without overlapping any lines.
            Do not waste time overthinking the hypothesis. Just generate the Python code for the drawing.
            Make sure to include 'plt.show()' at the end of the script.
            When using plt.hlines(), always use xmin and xmax instead of xleft and xright.
            If the hypothesis presents a 3D figure, provide a model that can be rotated.
            Make sure the background is white and axes are not visible.
            Please make sure to include every point mentioned in the hypothesis, even if they appear in the conclusion of said hypothesis.
            Hypothesis: {hypothesis}
            """
        )
        response_text = response.text

        python_code = extract_python_code(response_text)
        with open(OUTPUT_FILE, "w", encoding='utf-8') as file:
            file.write(python_code)
        
        drawing_queue.put(python_code)
        root.after(100, execute_drawing)
        
    except Exception as e:
        messagebox.showerror("Error", f"Drawing generation failed: {str(e)}")

def update_solution():
    """Update solution text in GUI"""
    global streamed_solution_text
    try:
        solution_chunk = solution_queue.get_nowait()
        solution_chunk = solution_chunk.replace("**", "")
        solution_chunk = solution_chunk.replace("`", "")

        new_text = streamed_solution_text.get() + solution_chunk
        streamed_solution_text.set(new_text)
        solution_text.config(state=tk.NORMAL)
        solution_text.delete("1.0", tk.END)
        solution_text.insert("1.0", streamed_solution_text.get())
        solution_text.config(state=tk.DISABLED)
        solution_queue.task_done()
    except queue.Empty:
        pass

def generate_solution(hypothesis):
    """Generate solution using AI"""
    try:
        stream = gemini_client.models.generate_content_stream(
            model="gemini-2.5-pro",
            contents=[{"parts": [{"text": f"""You will be sent a mathematical (geometrical) hypothesis in natural language. 
Please provide back a clear explanation of the solution to the hypothesis. 
Please do not use exaggerated language or overly complex explanations. 
Please do not get stuck in the details and complex or hard arithmetic, but provide a clear and concise explanation of the solution. 
Please do not provide any code or instructions, just the solution itself. 
Please provide a solution in the same language as the following hypothesis.
Please provide a mostly mathematical explanation, preferably using mathematical terms and symbols, but, if strictly necessary, you can use natural language as well.
Please use, in the actual solution, the least amount of natural language you can.
Please avoid vectors and slopes and use geometry at all costs. Provide a verbose and explanatory solution in the same language as the given hypothesis, but make it preferably mathematical, without much natural language. 
VECTORS ARE STRICTLY PROHIBITED, UNLESS THE WORD VECTOR IS MENTIONED IN THE FOLLOWING HYPOTHESIS.
Hypothesis: {hypothesis}"""}]}]
        )

        for chunk in stream:
            if getattr(chunk, 'text', None):
                solution_queue.put(chunk.text)
                root.after(100, update_solution)
        
    except Exception as e:
        messagebox.showerror("Error", f"Solution generation failed: {str(e)}")

def generate_pdf():
    """Generate PDF with hypothesis, drawing, and solution"""
    try:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save PDF As"
        )
        
        if not file_path:
            return
        
        hypothesis = input_text.get("1.0", tk.END).strip()
        solution = solution_text.get("1.0", tk.END).strip()
        
        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter
        
        # Add hypothesis
        c.setFont(PDF_FONT, 14)
        y = height - 50
        c.drawString(50, y, "Hypothesis:")
        c.setFont(PDF_FONT, 12)
        y -= 20
        
        words = hypothesis.split()
        line = []
        for word in words:
            line.append(word)
            if c.stringWidth(' '.join(line), PDF_FONT, 12) > width - 100:
                line.pop()
                c.drawString(50, y, ' '.join(line))
                line = [word]
                y -= 20
                if y < 50:
                    c.showPage()
                    y = height - 50
        if line:
            c.drawString(50, y, ' '.join(line))
            y -= 40
        
        # Add drawing
        if hasattr(plt, 'get_fignums') and plt.get_fignums():
            temp_png = os.path.join(TEMP_DIR, "temp_drawing.png")
            plt.savefig(temp_png, dpi=300, bbox_inches='tight', facecolor='white')
            
            img = Image.open(temp_png)
            img_width, img_height = img.size
            
            scale = min((width - 100) / img_width, 300 / img_height)
            new_width = img_width * scale
            new_height = img_height * scale
            
            x_offset = (width - new_width) / 2
            c.drawImage(temp_png, x_offset, y - new_height, 
                       width=new_width, height=new_height)
            y = y - new_height - 40
            
            try:
                os.remove(temp_png)
            except:
                pass
        
        # Add solution
        c.setFont(PDF_FONT, 14)
        c.drawString(50, y, "Solution:")
        c.setFont(PDF_FONT, 12)
        y -= 20
        
        words = solution.split()
        line = []
        for word in words:
            line.append(word)
            if c.stringWidth(' '.join(line), PDF_FONT, 12) > width - 100:
                line.pop()
                c.drawString(50, y, ' '.join(line))
                line = [word]
                y -= 20
                if y < 50:
                    c.showPage()
                    c.setFont(PDF_FONT, 12)
                    y = height - 50
        if line:
            c.drawString(50, y, ' '.join(line))
        
        c.save()
        messagebox.showinfo("Success", f"PDF saved to {file_path}")
        
    except Exception as e:
        messagebox.showerror("Error", f"PDF generation failed: {str(e)}")

def generate_both():
    """Generate both drawing and solution"""
    hypothesis = input_text.get("1.0", tk.END).strip()
    if not hypothesis:
        messagebox.showerror("Error", "Please enter a hypothesis.")
        return
    
    generate_button.config(state=tk.DISABLED)
    
    drawing_thread = threading.Thread(target=generate_geometry, args=(hypothesis,))
    solution_thread = threading.Thread(target=generate_solution, args=(hypothesis,))
    
    drawing_thread.start()
    solution_thread.start()
    
    def check_threads():
        if drawing_thread.is_alive() or solution_thread.is_alive():
            root.after(500, check_threads)
        else:
            generate_button.config(state=tk.NORMAL)
    
    check_threads()

def on_closing():
    """Handle window closing"""
    plt.close('all')
    root.destroy()


# Create GUI
root = tk.Tk()
streamed_solution_text = tk.StringVar()
root.title("Geometry AI")

# Get system screen size and apply dynamically
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
root.geometry(f"{screen_width}x{screen_height}")

# Determine light or dark mode based on default background color
default_bg = root.cget('bg')
is_dark_mode = default_bg.lower() not in ('white', '#ffffff')

BG_COLOR = '#1E1E1E' if is_dark_mode else 'white'
TEXT_COLOR = 'white' if is_dark_mode else 'black'
TEXTBOX_BG = '#2a2a2a' if is_dark_mode else '#F9F9F9'
BORDER_COLOR = '#3a3a3a' if is_dark_mode else '#CCCCCC'

root.configure(bg=BG_COLOR)

style = ttk.Style()
style.theme_use('clam')
style.configure('TLabel', background=BG_COLOR, foreground=TEXT_COLOR, font=('SF Pro Display', 14))
style.configure('TButton', background='#007AFF', foreground='white', font=('SF Pro Display', 14), padding=6)
style.map('TButton', background=[('active', '#005BBB')])
root.protocol("WM_DELETE_WINDOW", on_closing)

# Input area
input_label = ttk.Label(root, text="Enter Hypothesis:")
input_label.pack(pady=5, padx=20, anchor='w')
input_text = tk.Text(root, height=7, font=('SF Pro Display', 14), bg=TEXTBOX_BG, fg=TEXT_COLOR, relief='flat', insertbackground=TEXT_COLOR)
input_text.pack(pady=5, padx=20, fill='x', expand=True)

# Generate button
generate_button = ttk.Button(root, text="Generate Drawing & Solution", command=generate_both)
generate_button.pack(pady=(15, 10), padx=20)

# Solution area
solution_label = ttk.Label(root, text="Solution:")
solution_label.pack(pady=5, padx=20, anchor='w')
solution_text = tk.Text(root, height=30, font=('SF Pro Display', 14), bg=TEXTBOX_BG, fg=TEXT_COLOR, relief='flat', insertbackground=TEXT_COLOR)
solution_text.pack(pady=5, padx=20, fill='both', expand=True)

# PDF button
pdf_button = ttk.Button(root, text="Download PDF", command=generate_pdf)
pdf_button.pack(pady=(10, 20), padx=20)

# Warning label
warning_label = ttk.Label(
    root,
    text="⚠️ The solution is generated by AI and may be inaccurate. Please verify the solution.",
    foreground="red",
    background=BG_COLOR,
    font=('SF Pro Display', 13)
)
warning_label.pack(pady=10, padx=20)

# Start application
if __name__ == "__main__":
    root.mainloop()