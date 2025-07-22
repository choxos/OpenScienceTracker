from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, ResearchField, Paper, Journal

class UserProfileForm(forms.ModelForm):
    """Form for editing user profiles"""
    
    class Meta:
        model = UserProfile
        fields = ['institution', 'research_interests', 'is_researcher', 'orcid', 
                 'preferred_fields', 'email_notifications']
        widgets = {
            'institution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your institution or organization'
            }),
            'research_interests': forms.CheckboxSelectMultiple(),
            'preferred_fields': forms.CheckboxSelectMultiple(),
            'orcid': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0000-0000-0000-0000'
            }),
            'is_researcher': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'orcid': 'Enter your ORCID identifier in the format 0000-0000-0000-0000',
            'research_interests': 'Select your research areas of interest',
            'preferred_fields': 'Select fields you want to see highlighted in your dashboard',
        }

class PaperSearchForm(forms.Form):
    """Form for advanced paper search"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search titles, authors, or journals...'
        })
    )
    
    year_from = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'From year'
        })
    )
    
    year_to = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'To year'
        })
    )
    
    journal = forms.ModelChoiceField(
        queryset=Journal.objects.all(),
        required=False,
        empty_label="All journals",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Transparency indicators filters
    data_sharing = forms.BooleanField(
        required=False,
        label="Data sharing available",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    code_sharing = forms.BooleanField(
        required=False,
        label="Code sharing available",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    coi_disclosure = forms.BooleanField(
        required=False,
        label="COI disclosure available",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    funding_disclosure = forms.BooleanField(
        required=False,
        label="Funding disclosure available",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    protocol_registration = forms.BooleanField(
        required=False,
        label="Protocol registration available",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Transparency score range
    transparency_score_min = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=7,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min score (0-7)'
        })
    )
    
    transparency_score_max = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=7,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max score (0-7)'
        })
    )
    
    # Sorting options
    SORT_CHOICES = [
        ('-pub_year', 'Publication year (newest first)'),
        ('pub_year', 'Publication year (oldest first)'),
        ('title', 'Title (A-Z)'),
        ('-title', 'Title (Z-A)'),
        ('-transparency_score', 'Transparency score (highest first)'),
        ('transparency_score', 'Transparency score (lowest first)'),
        ('journal_title', 'Journal (A-Z)'),
        ('-created_at', 'Recently added'),
    ]
    
    order_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='-pub_year',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class JournalSearchForm(forms.Form):
    """Form for advanced journal search"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search journal names or publishers...'
        })
    )
    
    country = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    subject = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All subjects'),
            ('Dentistry', 'Dentistry'),
            ('Orthodontics', 'Orthodontics'),
            ('Medicine', 'Medicine'),
            ('Surgery', 'Surgery'),
            ('Cardiology', 'Cardiology'),
            ('Neurology', 'Neurology'),
            ('Pediatrics', 'Pediatrics'),
            ('Psychiatry', 'Psychiatry'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    language = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All languages'),
            ('English', 'English'),
            ('German', 'German'),
            ('French', 'French'),
            ('Spanish', 'Spanish'),
            ('Italian', 'Italian'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Indexing status
    currently_indexed = forms.BooleanField(
        required=False,
        label="Currently indexed for MEDLINE",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Publication period
    start_year_from = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Started after year'
        })
    )
    
    start_year_to = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Started before year'
        })
    )
    
    # Paper count range
    min_papers = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum papers'
        })
    )
    
    # Sorting options
    SORT_CHOICES = [
        ('title_abbreviation', 'Title (A-Z)'),
        ('-title_abbreviation', 'Title (Z-A)'),
        ('-paper_count', 'Paper count (most first)'),
        ('paper_count', 'Paper count (least first)'),
        ('-avg_transparency', 'Avg transparency (highest first)'),
        ('avg_transparency', 'Avg transparency (lowest first)'),
        ('country', 'Country (A-Z)'),
        ('-publication_start_year', 'Start year (newest first)'),
        ('publication_start_year', 'Start year (oldest first)'),
    ]
    
    order_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        initial='title_abbreviation',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate country choices dynamically
        countries = Journal.objects.values_list('country', flat=True).distinct().order_by('country')
        country_choices = [('', 'All countries')] + [(c, c) for c in countries if c]
        self.fields['country'].choices = country_choices

class ContactForm(forms.Form):
    """Contact form for user feedback"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email'
        })
    )
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Your message'
        })
    )
    
    MESSAGE_TYPES = [
        ('feedback', 'General Feedback'),
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('data', 'Data Issue'),
        ('other', 'Other'),
    ]
    
    message_type = forms.ChoiceField(
        choices=MESSAGE_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class DataExportForm(forms.Form):
    """Form for customizing data exports"""
    
    EXPORT_FORMATS = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xlsx', 'Excel'),
    ]
    
    format = forms.ChoiceField(
        choices=EXPORT_FORMATS,
        initial='csv',
        widget=forms.RadioSelect()
    )
    
    # Date range
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    # Fields to include
    include_transparency_scores = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    include_journal_info = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    include_author_info = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Filter by research field
    research_fields = forms.ModelMultipleChoiceField(
        queryset=ResearchField.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

class BulkActionForm(forms.Form):
    """Form for bulk actions on papers or journals"""
    
    ACTIONS = [
        ('export', 'Export selected items'),
        ('update_transparency', 'Recalculate transparency scores'),
        ('mark_reviewed', 'Mark as reviewed'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTIONS,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    selected_items = forms.CharField(
        widget=forms.HiddenInput()
    )

class AdvancedFilterForm(forms.Form):
    """Advanced filtering form for statistical analysis"""
    
    # Publication period
    pub_year_start = forms.IntegerField(
        required=False,
        min_value=1900,
        max_value=2030,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Start year'
        })
    )
    
    pub_year_end = forms.IntegerField(
        required=False,
        min_value=1900,
        max_value=2030,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'End year'
        })
    )
    
    # Research fields
    research_fields = forms.ModelMultipleChoiceField(
        queryset=ResearchField.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    
    # Journal characteristics
    journal_countries = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    
    # Transparency thresholds
    min_transparency_score = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=7,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min transparency score'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate country choices
        countries = Journal.objects.values_list('country', flat=True).distinct().order_by('country')
        country_choices = [(c, c) for c in countries if c]
        self.fields['journal_countries'].choices = country_choices 