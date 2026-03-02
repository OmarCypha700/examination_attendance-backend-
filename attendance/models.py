from django.db import models
from django.conf import settings


class Program(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.name}"


class Level(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Student(models.Model):
    GENDER_CHOICES = [("M", "Male"), ("F", "Female")]

    index_number = models.CharField(max_length=50, unique=True, db_index=True)
    full_name    = models.CharField(max_length=200)
    programme    = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="students")
    level        = models.ForeignKey(Level,   on_delete=models.PROTECT, related_name="students")
    gender       = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)

    # QR payload – the lookup key during scanning
    qr_code      = models.CharField(max_length=255, unique=True, db_index=True)

    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["index_number"]
        indexes  = [models.Index(fields=["qr_code"])]

    def __str__(self):
        return f"{self.index_number} – {self.full_name}"


class Course(models.Model):
    course_code  = models.CharField(max_length=20, unique=True)
    course_title = models.CharField(max_length=200)
    programme    = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="courses")
    level        = models.ForeignKey(Level,   on_delete=models.PROTECT, related_name="courses")

    class Meta:
        ordering = ["course_code"]

    def __str__(self):
        return f"{self.course_code} – {self.course_title}"


class ExamSession(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("active",    "Active"),
        ("closed",    "Closed"),
    ]

    course            = models.ForeignKey(Course,   on_delete=models.PROTECT, related_name="exam_sessions")
    programme         = models.ForeignKey(Program,  on_delete=models.PROTECT, related_name="exam_sessions")
    level             = models.ForeignKey(Level,    on_delete=models.PROTECT, related_name="exam_sessions")
    date              = models.DateField()
    start_time        = models.TimeField()
    end_time          = models.TimeField(null=True, blank=True)
    venue             = models.CharField(max_length=200, blank=True)
    expected_students = models.PositiveIntegerField(default=0)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    created_by        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-start_time"]
        indexes  = [
            models.Index(fields=["status"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.course} | {self.date}"

    @property
    def attendance_summary(self):
        qs = self.attendances.all()
        return {
            "total":     qs.count(),
            "section_a": qs.filter(section="A").count(),
            "section_b": qs.filter(section="B").count(),
            "present":   qs.filter(status="present").count(),
            "duplicate": qs.filter(status="duplicate").count(),
            "invalid":   qs.filter(status="invalid").count(),
        }


class ExamAttendance(models.Model):
    """One record per student per section per exam session."""

    SECTION_CHOICES = [
        ("A", "Section A – Objective"),
        ("B", "Section B – Theory"),
    ]

    STATUS_CHOICES = [
        ("present",   "Present"),
        ("duplicate", "Duplicate"),
        ("invalid",   "Invalid"),
    ]

    student      = models.ForeignKey(Student,     on_delete=models.PROTECT, related_name="attendances")
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE,  related_name="attendances")
    section      = models.CharField(max_length=1, choices=SECTION_CHOICES)
    scanned_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    scan_time    = models.DateTimeField(auto_now_add=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="present")
    remarks      = models.TextField(blank=True)

    class Meta:
        unique_together = [["student", "exam_session", "section"]]
        ordering        = ["scan_time"]
        indexes         = [
            models.Index(fields=["exam_session", "section"]),
            models.Index(fields=["scan_time"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.student.index_number} | {self.exam_session} | {self.section}"
