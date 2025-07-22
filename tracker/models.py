from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

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
    """Model representing a scientific paper"""
    # Article identifiers
    pmid = models.CharField(max_length=20, unique=True, db_index=True)
    pmcid = models.CharField(max_length=20, null=True, blank=True)
    doi = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    
    # Basic information
    title = models.TextField()
    author_string = models.TextField()
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name='papers')
    journal_title = models.CharField(max_length=200, db_index=True)  # For backward compatibility
    
    # Publication details
    pub_year = models.IntegerField(db_index=True)
    pub_year_modified = models.CharField(max_length=20, null=True, blank=True)
    first_publication_date = models.DateField(null=True, blank=True)
    year_first_pub = models.IntegerField(null=True, blank=True)
    month_first_pub = models.IntegerField(null=True, blank=True)
    
    # Europe PMC publication details
    issue = models.CharField(max_length=20, null=True, blank=True, help_text="Journal issue number")
    page_info = models.CharField(max_length=50, null=True, blank=True, help_text="Page information")
    journal_volume = models.CharField(max_length=20, null=True, blank=True, help_text="Journal volume")
    pub_type = models.CharField(max_length=200, null=True, blank=True, help_text="Publication type from Europe PMC")
    
    # Europe PMC availability flags
    is_open_access = models.BooleanField(default=False, help_text="Open access availability")
    in_epmc = models.BooleanField(default=False, help_text="Available in Europe PMC")
    in_pmc = models.BooleanField(default=False, help_text="Available in PMC")
    has_pdf = models.BooleanField(default=False, help_text="PDF available")
    
    # Journal metrics and categorization
    journal_issn = models.CharField(max_length=9, null=True, blank=True)
    jif2020 = models.FloatField(null=True, blank=True, help_text="Journal Impact Factor 2020")
    scimago_publisher = models.CharField(max_length=500, null=True, blank=True)
    broad_subject_category = models.CharField(max_length=200, null=True, blank=True, db_index=True, 
                                            help_text="Primary broad subject category from NLM")
    
    # Transparency indicators (5 core + 3 additional)
    is_open_data = models.BooleanField(default=False, help_text="Data sharing available")
    is_open_code = models.BooleanField(default=False, help_text="Code sharing available")
    is_coi_pred = models.BooleanField(default=False, help_text="Conflict of interest disclosure")
    is_fund_pred = models.BooleanField(default=False, help_text="Funding disclosure")
    is_register_pred = models.BooleanField(default=False, help_text="Protocol registration")
    is_replication = models.BooleanField(null=True, blank=True, help_text="Replication component")
    is_novelty = models.BooleanField(null=True, blank=True, help_text="Novelty statement")
    
    # Disclosure text indicators
    disc_data = models.BooleanField(default=False, help_text="Data disclosure statement found")
    disc_code = models.BooleanField(default=False, help_text="Code disclosure statement found")
    disc_coi = models.BooleanField(default=False, help_text="COI disclosure statement found")
    disc_fund = models.BooleanField(default=False, help_text="Funding disclosure statement found")
    disc_register = models.BooleanField(default=False, help_text="Registration disclosure statement found")
    disc_replication = models.BooleanField(null=True, blank=True, help_text="Replication disclosure found")
    disc_novelty = models.BooleanField(null=True, blank=True, help_text="Novelty disclosure found")
    
    # Calculated transparency metrics
    transparency_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(8)],
        help_text="Total transparency score (0-8)"
    )
    transparency_score_pct = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Transparency score as percentage"
    )
    
    # Assessment metadata
    assessment_date = models.DateTimeField(null=True, blank=True)
    assessment_tool = models.CharField(max_length=50, default='rtransparent')
    ost_version = models.CharField(max_length=10, default='1.0')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-pub_year', 'title']
        indexes = [
            models.Index(fields=['pub_year']),
            models.Index(fields=['journal_title']),
            models.Index(fields=['transparency_score']),
            models.Index(fields=['is_open_data']),
            models.Index(fields=['is_open_code']),
        ]
    
    def __str__(self):
        return f"{self.title[:50]} ({self.pub_year})"
    
    def calculate_transparency_score(self):
        """Calculate transparency score based on 8 indicators"""
        score = 0
        indicators = [
            self.is_open_data,
            self.is_open_code,
            self.is_coi_pred,
            self.is_fund_pred,
            self.is_register_pred,
            self.is_open_access,  # New Open Access indicator
        ]
        
        # Count core 6 indicators (5 original + Open Access)
        score += sum(1 for indicator in indicators if indicator)
        
        # Add additional indicators if available
        if self.is_replication is not None and self.is_replication:
            score += 1
        if self.is_novelty is not None and self.is_novelty:
            score += 1
            
        return score
    
    def get_transparency_percentage(self):
        """Get transparency score as percentage (out of available indicators)"""
        max_score = 5  # Basic indicators always available
        if self.is_replication is not None:
            max_score += 1
        if self.is_novelty is not None:
            max_score += 1
        
        if max_score == 0:
            return 0.0
        return (self.transparency_score / max_score) * 100
    
    def save(self, *args, **kwargs):
        """Override save to automatically calculate transparency score"""
        self.transparency_score = self.calculate_transparency_score()
        self.transparency_score_pct = self.get_transparency_percentage()
        super().save(*args, **kwargs)

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
