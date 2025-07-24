from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from postgres_copy import CopyManager
from .managers import OptimizedPaperManager

class Journal(models.Model):
    """Model representing a scientific journal"""
    nlm_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    title_abbreviation = models.CharField(max_length=200, db_index=True)
    title_full = models.TextField()
    authors = models.TextField(null=True, blank=True)
    
    # Publication details
    publication_start_year = models.IntegerField(null=True, blank=True)
    publication_end_year = models.IntegerField(null=True, blank=True)
    frequency = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    publisher = models.CharField(max_length=500, null=True, blank=True, db_index=True)
    language = models.CharField(max_length=100, null=True, blank=True)
    
    # ISSN information
    issn_electronic = models.CharField(max_length=9, null=True, blank=True)
    issn_print = models.CharField(max_length=9, null=True, blank=True)
    issn_linking = models.CharField(max_length=9, null=True, blank=True)
    
    # Indexing and classification
    indexing_status = models.CharField(max_length=200, null=True, blank=True)
    broad_subject_terms = models.TextField(help_text="Semicolon-separated subject terms")
    subject_term_count = models.IntegerField(default=1)
    mesh_terms = models.TextField(null=True, blank=True)
    
    # Metadata
    lccn = models.CharField(max_length=50, null=True, blank=True)
    electronic_links = models.URLField(null=True, blank=True)
    publication_types = models.CharField(max_length=200, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Additional metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add CopyManager for fast CSV imports
    objects = CopyManager()
    
    @property
    def broad_subject_terms_list(self):
        """Return broad subject terms as a list"""
        if self.broad_subject_terms:
            return [term.strip() for term in self.broad_subject_terms.split(';') if term.strip()]
        return []
    
    @property
    def issn(self):
        """Return the best available ISSN"""
        return self.issn_print or self.issn_electronic or self.issn_linking
    
    @property
    def publication_years(self):
        """Return formatted publication years"""
        if self.publication_start_year and self.publication_end_year:
            if self.publication_start_year == self.publication_end_year:
                return str(self.publication_start_year)
            return f"{self.publication_start_year}-{self.publication_end_year}"
        elif self.publication_start_year:
            return f"{self.publication_start_year}-present"
        return "Unknown"

    class Meta:
        ordering = ['title_abbreviation']
        indexes = [
            models.Index(fields=['country']),
            models.Index(fields=['publisher']),
            models.Index(fields=['publication_start_year']),
        ]
    
    def __str__(self):
        return f"{self.title_abbreviation} - {self.title_full[:50]}"
    
    def is_dental_journal(self):
        """Check if this is a dental or orthodontics journal"""
        if not self.broad_subject_terms:
            return False
        return 'Dentistry' in self.broad_subject_terms or 'Orthodontics' in self.broad_subject_terms

class Paper(models.Model):
    """Model representing a scientific paper from EuropePMC with transparency indicators"""
    
    # === EuropePMC Core Fields ===
    # Article identifiers
    epmc_id = models.CharField(max_length=50, unique=True, db_index=True, help_text="EuropePMC ID (primary key)")
    source = models.CharField(max_length=20, help_text="Data source (e.g., PMC, MED)")
    pmcid = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="PubMed Central ID")
    pmid = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="PubMed ID")
    doi = models.CharField(max_length=200, null=True, blank=True, db_index=True, help_text="Digital Object Identifier")
    
    # Article content
    title = models.TextField(help_text="Article title")
    author_string = models.TextField(null=True, blank=True, help_text="Author names as string")
    
    # Journal information
    journal = models.ForeignKey(Journal, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    journal_title = models.CharField(max_length=500, db_index=True, help_text="Journal title from EuropePMC")
    journal_issn = models.CharField(max_length=20, null=True, blank=True, help_text="Journal ISSN")
    
    # Publication details
    pub_year = models.IntegerField(null=True, blank=True, db_index=True, help_text="Publication year")
    issue = models.CharField(max_length=50, null=True, blank=True, help_text="Journal issue")
    journal_volume = models.CharField(max_length=50, null=True, blank=True, help_text="Journal volume")
    page_info = models.CharField(max_length=100, null=True, blank=True, help_text="Page information")
    pub_type = models.CharField(max_length=500, null=True, blank=True, help_text="Publication type")
    
    # Dates
    first_index_date = models.DateField(null=True, blank=True, help_text="First index date in EuropePMC")
    first_publication_date = models.DateField(null=True, blank=True, help_text="First publication date")
    
    # Access and availability flags
    is_open_access = models.BooleanField(default=False, help_text="Open access status")
    in_epmc = models.BooleanField(default=False, help_text="Available in EuropePMC")
    in_pmc = models.BooleanField(default=False, help_text="Available in PMC")
    has_pdf = models.BooleanField(default=False, help_text="PDF available")
    has_book = models.BooleanField(default=False, help_text="Book chapter available")
    has_suppl = models.BooleanField(default=False, help_text="Supplementary material available")
    
    # Content flags
    has_references = models.BooleanField(default=False, help_text="References available")
    has_text_mined_terms = models.BooleanField(default=False, help_text="Text-mined terms available")
    has_db_cross_references = models.BooleanField(default=False, help_text="Database cross-references available")
    has_labs_links = models.BooleanField(default=False, help_text="Lab links available")
    has_tm_accession_numbers = models.BooleanField(default=False, help_text="Text-mined accession numbers available")
    
    # Citation metrics
    cited_by_count = models.IntegerField(default=0, help_text="Citation count from EuropePMC")
    
    # === Transparency Indicators from rtransparent ===
    # Conflict of Interest
    is_coi_pred = models.BooleanField(default=False, help_text="Has conflict of interest disclosure")
    coi_text = models.TextField(null=True, blank=True, help_text="Conflict of interest disclosure text")
    
    # Funding
    is_fund_pred = models.BooleanField(default=False, help_text="Has funding disclosure")
    fund_text = models.TextField(null=True, blank=True, help_text="Funding disclosure text")
    
    # Registration
    is_register_pred = models.BooleanField(default=False, help_text="Study was pre-registered")
    register_text = models.TextField(null=True, blank=True, help_text="Registration statement text")
    
    # Open Data
    is_open_data = models.BooleanField(default=False, help_text="Has open data available")
    open_data_category = models.CharField(max_length=200, null=True, blank=True, help_text="Category of open data")
    open_data_statements = models.TextField(null=True, blank=True, help_text="Open data statement text")
    
    # Open Code
    is_open_code = models.BooleanField(default=False, help_text="Has open code available")
    open_code_statements = models.TextField(null=True, blank=True, help_text="Open code statement text")
    
    # === Subject Classification ===
    broad_subject_term = models.CharField(max_length=200, null=True, blank=True, db_index=True, 
                                        help_text="NLM broad subject classification for this paper's journal")
    
    # === Calculated Fields ===
    transparency_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="Total transparency score (0-6): COI + Funding + Registration + Open Data + Open Code + Open Access"
    )
    transparency_score_pct = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Transparency score as percentage"
    )
    
    # === Metadata ===
    # Processing flags
    transparency_processed = models.BooleanField(default=False, help_text="Whether transparency indicators have been processed")
    processing_date = models.DateTimeField(null=True, blank=True, help_text="Date when transparency processing was completed")
    
    # System metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add optimized manager
    objects = OptimizedPaperManager()
    
    class Meta:
        ordering = ['-pub_year', 'title']
        indexes = [
            models.Index(fields=['epmc_id']),
            models.Index(fields=['pmid']),
            models.Index(fields=['pmcid']),
            models.Index(fields=['doi']),
            models.Index(fields=['pub_year']),
            models.Index(fields=['journal_title']),
            models.Index(fields=['is_open_access']),
            models.Index(fields=['transparency_score']),
            models.Index(fields=['is_open_data']),
            models.Index(fields=['is_open_code']),
            models.Index(fields=['is_coi_pred']),
            models.Index(fields=['is_fund_pred']),
            models.Index(fields=['is_register_pred']),
            models.Index(fields=['transparency_processed']),
        ]
    
    def __str__(self):
        return f"{self.title[:50]} ({self.pub_year})"
    
    def calculate_transparency_score(self):
        """Calculate transparency score based on 6 indicators"""
        score = 0
        indicators = [
            self.is_coi_pred,      # Conflict of interest disclosure
            self.is_fund_pred,     # Funding disclosure  
            self.is_register_pred, # Pre-registration
            self.is_open_data,     # Open data
            self.is_open_code,     # Open code
            self.is_open_access,   # Open access
        ]
        
        score = sum(1 for indicator in indicators if indicator)
        return score
    
    def get_transparency_percentage(self):
        """Get transparency score as percentage (out of 6 indicators)"""
        return round((self.transparency_score / 6.0) * 100, 1)
    
    def save(self, *args, **kwargs):
        """Override save to calculate transparency score"""
        self.transparency_score = self.calculate_transparency_score()
        self.transparency_score_pct = self.get_transparency_percentage()
        super().save(*args, **kwargs)
    
    def get_identifiers_dict(self):
        """Get all available identifiers as dictionary"""
        identifiers = {}
        if self.pmid:
            identifiers['pmid'] = self.pmid
        if self.pmcid:
            identifiers['pmcid'] = self.pmcid
        if self.doi:
            identifiers['doi'] = self.doi
        if self.epmc_id:
            identifiers['epmc_id'] = self.epmc_id
        return identifiers

class ResearchField(models.Model):
    """Model for research fields/disciplines"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    parent_field = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    
    # Statistics
    total_journals = models.IntegerField(default=0)
    total_papers = models.IntegerField(default=0)
    avg_transparency_score = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class UserProfile(models.Model):
    """Extended user profile for OST users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    institution = models.CharField(max_length=200, null=True, blank=True)
    research_interests = models.ManyToManyField(ResearchField, blank=True)
    is_researcher = models.BooleanField(default=True)
    orcid = models.CharField(max_length=19, null=True, blank=True, help_text="ORCID ID (e.g., 0000-0000-0000-0000)")
    
    # Preferences
    preferred_fields = models.ManyToManyField(ResearchField, related_name='preferred_by_users', blank=True)
    email_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.institution}"

class TransparencyTrend(models.Model):
    """Model to store transparency trends over time"""
    year = models.IntegerField(db_index=True)
    month = models.IntegerField(null=True, blank=True)
    field = models.ForeignKey(ResearchField, on_delete=models.CASCADE)
    
    # Transparency metrics
    total_papers = models.IntegerField(default=0)
    data_sharing_count = models.IntegerField(default=0)
    code_sharing_count = models.IntegerField(default=0)
    coi_disclosure_count = models.IntegerField(default=0)
    funding_disclosure_count = models.IntegerField(default=0)
    protocol_registration_count = models.IntegerField(default=0)
    replication_count = models.IntegerField(default=0)
    novelty_count = models.IntegerField(default=0)
    
    # Percentages
    data_sharing_pct = models.FloatField(default=0.0)
    code_sharing_pct = models.FloatField(default=0.0)
    coi_disclosure_pct = models.FloatField(default=0.0)
    funding_disclosure_pct = models.FloatField(default=0.0)
    protocol_registration_pct = models.FloatField(default=0.0)
    replication_pct = models.FloatField(default=0.0)
    novelty_pct = models.FloatField(default=0.0)
    
    avg_transparency_score = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['year', 'month', 'field']
        ordering = ['year', 'month']
    
    def __str__(self):
        date_str = f"{self.year}-{self.month:02d}" if self.month else str(self.year)
        return f"{self.field.name} - {date_str}"
