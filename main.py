import os
import re
import pandas as pd
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.textinput import TextInput

class ResumeExtractorApp(App):
    def build(self):
        Window.clearcolor = (1, 1, 1, 1)  # Set background color
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        # Horizontal layout for buttons at the top
        button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)

        self.upload_button = Button(text='Upload Resumes', background_color=(0.2, 0.6, 0.8, 1))
        self.upload_button.bind(on_press=self.open_file_chooser)
        button_layout.add_widget(self.upload_button)

        self.process_button = Button(text='Process Resumes', background_color=(0.4, 0.8, 0.4, 1))
        self.process_button.bind(on_press=self.extract_data)
        button_layout.add_widget(self.process_button)

        self.export_button = Button(text='Export to CSV', background_color=(0.8, 0.4, 0.4, 1))
        self.export_button.bind(on_press=self.select_directory)
        button_layout.add_widget(self.export_button)

        layout.add_widget(button_layout)  # Add the button layout to the main layout at the top

        self.label = Label(size_hint_y=None, height=50, color=(0, 0, 0, 1))
        layout.add_widget(self.label)

        self.progress_bar = ProgressBar(max=100, size_hint_y=None, height=20)
        layout.add_widget(self.progress_bar)

        self.data_display = TextInput(size_hint_y=None, height=200, readonly=True, background_color=(0.9, 0.9, 0.9, 1))
        layout.add_widget(self.data_display)

        self.all_data = []  # To store parsed resume data
        self.file_paths = []  # To store selected file paths
        self.save_directory = os.path.join(os.path.expanduser("~"), "Downloads")  # Default save directory

        return layout

    def open_file_chooser(self, instance):
        """Open the file chooser to select resumes."""
        content = BoxLayout(orientation='vertical')
        self.file_chooser = FileChooserIconView(multiselect=True, filters=['*.pdf', '*.docx'])
        content.add_widget(self.file_chooser)

        select_button = Button(text='Select', size_hint_y=None, height=50)
        select_button.bind(on_press=self.select_files)
        content.add_widget(select_button)

        self.file_chooser_popup = Popup(title="Select Resumes", content=content, size_hint=(0.9, 0.9))
        self.file_chooser_popup.open()

    def select_files(self, instance):
        """Handle file selection from the file chooser."""
        self.file_paths = self.file_chooser.selection  # Store selected file paths
        if self.file_paths:
            self.all_data.clear()  # Clear any previously uploaded data
            self.label.text = f"{len(self.file_paths)} resumes uploaded, ready to process."
            self.file_chooser_popup.dismiss()  # Close the file chooser popup

    def extract_data(self, instance):
        if not self.file_paths:
            self.label.text = "No resumes uploaded."
            return

        self.progress_bar.value = 0
        self.all_data.clear()  # Clear previous data before extraction
        for idx, file_path in enumerate(self.file_paths):
            try:
                resume_data = self.parse_resume(file_path)
                if resume_data:
                    self.all_data.append(resume_data)
            except Exception as e:
                self.label.text = f"Error processing {file_path}: {e}"
                continue
            self.progress_bar.value = ((idx + 1) / len(self.file_paths)) * 100  # Update progress

        if self.all_data:
            self.label.text = "Data extraction complete!"
            self.display_extracted_data()  # Show the extracted data
        else:
            self.label.text = "No valid data extracted."
        self.progress_bar.value = 0  # Reset progress bar after processing

    def display_extracted_data(self):
        """Display the extracted data in the text input."""
        self.data_display.text = ""
        for entry in self.all_data:
            self.data_display.text += f"Name: {entry['Name']}, Email: {entry['Email']}, Contact Number: {entry['Contact Number']}\n"

    def select_directory(self, instance):
        """Open directory chooser for saving CSV file."""
        content = BoxLayout(orientation='vertical')
        self.directory_chooser = FileChooserIconView(path=self.save_directory, dirselect=True)
        content.add_widget(self.directory_chooser)

        select_button = Button(text='Select Directory', size_hint_y=None, height=50)
        select_button.bind(on_press=self.save_directory_selected)
        content.add_widget(select_button)

        self.directory_chooser_popup = Popup(title="Select Directory", content=content, size_hint=(0.9, 0.9))
        self.directory_chooser_popup.open()

    def save_directory_selected(self, instance):
        """Handle directory selection."""
        selected_dirs = self.directory_chooser.selection
        if selected_dirs:
            self.save_directory = selected_dirs[0]  # Get the selected directory
            self.label.text = f"CSV will be saved to: {self.save_directory}"
            self.directory_chooser_popup.dismiss()  # Close the directory chooser

            self.save_csv()  # Call save_csv to save immediately after selecting the directory
        else:
            self.label.text = "No directory selected."

    def save_csv(self):
        """Save the extracted data to a CSV file in the selected directory."""
        filename = os.path.join(self.save_directory, "extracted_data.csv")  # Save to selected directory
        self.create_csv(self.all_data, filename)
        self.label.text = f"CSV file created successfully at {filename}!"

    def parse_resume(self, file_path):
        """Parse the resume to extract Name, Email, and Contact Number."""
        text = self.extract_text_from_resume(file_path)
        if not text:
            raise ValueError("No text extracted from resume.")

        name = self.extract_name(text)
        email = self.extract_email(text)
        phone = self.extract_phone(text)

        return {"Name": name, "Email": email, "Contact Number": phone}

    def extract_text_from_resume(self, file_path):
        """Extract text from PDF or DOCX resume."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext == '.docx':
            return self.extract_text_from_docx(file_path)
        else:
            raise ValueError("Unsupported file type.")

    def extract_text_from_pdf(self, file_path):
        """Extract text from a PDF file."""
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text() + '\n' if page.extract_text() else ''
        return text

    def extract_text_from_docx(self, file_path):
        """Extract text from a DOCX file."""
        from docx import Document
        doc = Document(file_path)
        text = ''
        for paragraph in doc.paragraphs:
            text += paragraph.text + '\n'
        return text

    def extract_name(self, text):
        """Extract name using a simple heuristic (first line of the text)."""
        return text.splitlines()[0].strip()

    def extract_email(self, text):
        """Extract email using regex."""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else "N/A"

    def extract_phone(self, text):
        """Extract phone number using regex."""
        phone_pattern = r'\+?\d[\d -]{8,12}\d'
        phones = re.findall(phone_pattern, text)
        return phones[0] if phones else "N/A"

    def create_csv(self, data, filename):
        """Create a CSV file from the extracted data."""
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)

if __name__ == "__main__":
    ResumeExtractorApp().run()
