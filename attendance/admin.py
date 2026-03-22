from django.contrib import admin
from django.db.models import Count

from .models import (Course, ExamAttendance, ExamSession, Level, Program,
                     Student)


# =========================
# Program Admin
# =========================
@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")
    ordering = ("code",)


# =========================
# Level Admin
# =========================
@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)


# =========================
# Student Admin
# =========================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "index_number",
        "full_name",
        "programme",
        "level",
        "is_active",
        "created_at",
    )
    list_filter = ("programme", "level", "is_active")
    search_fields = ("index_number", "full_name", "qr_code")
    readonly_fields = ("created_at",)
    ordering = ("index_number",)
    list_select_related = ("programme", "level")


# =========================
# Course Admin
# =========================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_code", "course_title", "programme", "level")
    list_filter = ("programme", "level")
    search_fields = ("course_code", "course_title")
    ordering = ("course_code",)
    list_select_related = ("programme", "level")


# =========================
# ExamAttendance Inline
# =========================
class ExamAttendanceInline(admin.TabularInline):
    model = ExamAttendance
    extra = 0
    autocomplete_fields = ("student", "scanned_by")
    readonly_fields = ("scan_time",)
    show_change_link = True


# =========================
# ExamSession Admin
# =========================
@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "programme",
        "level",
        "date",
        "start_time",
        "status",
        "expected_students",
        "attendance_count",
    )
    list_filter = ("status", "programme", "level", "date")
    search_fields = ("course__course_code", "course__course_title", "venue")
    readonly_fields = ("created_at",)
    date_hierarchy = "date"
    inlines = [ExamAttendanceInline]
    list_select_related = ("course", "programme", "level", "created_by")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_attendance_count=Count("attendances"))

    def attendance_count(self, obj):
        return obj._attendance_count
    attendance_count.short_description = "Total Attendance"


# =========================
# ExamAttendance Admin
# =========================
@admin.register(ExamAttendance)
class ExamAttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "exam_session",
        "section",
        "status",
        "scanned_by",
        "scan_time",
    )
    list_filter = ("section", "status", "exam_session__date")
    search_fields = (
        "student__index_number",
        "student__full_name",
        "exam_session__course__course_code",
    )
    readonly_fields = ("scan_time",)
    autocomplete_fields = ("student", "exam_session", "scanned_by")
    list_select_related = ("student", "exam_session", "scanned_by")
    ordering = ("-scan_time",)