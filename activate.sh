#!/bin/bash
# Open Science Tracker - Virtual Environment Activation Script
# This script activates the virtual environment and provides helpful information

echo "🚀 Activating Open Science Tracker Virtual Environment..."
echo "📦 Virtual Environment: ost_env"
echo ""

# Activate the virtual environment
source ost_env/bin/activate

# Show current Python and pip versions
echo "✅ Virtual Environment Activated!"
echo "🐍 Python version: $(python --version)"
echo "📦 pip version: $(pip --version | cut -d' ' -f1-2)"
echo ""

echo "💡 Useful Commands:"
echo "   • Run Django server:     python manage.py runserver"
echo "   • Django admin:          python manage.py createsuperuser"
echo "   • Import data:           python import_dental_data_fixed.py"
echo "   • Process journals:      python create_journal_database.py"
echo "   • Create dental data:    python create_dental_ost_section.py"
echo "   • Deactivate:            deactivate"
echo ""

# Keep the shell active with the virtual environment
exec bash 