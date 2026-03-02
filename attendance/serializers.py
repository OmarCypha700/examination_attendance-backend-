from rest_framework import serializers
from .models import Program, Level, Student, Course, ExamSession, ExamAttendance


# ── Reference ────────────────────────────────────────────────────────────────

class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Program
        fields = "__all__"


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Level
        fields = "__all__"


# ── Student ──────────────────────────────────────────────────────────────────

class StudentSerializer(serializers.ModelSerializer):
    programme_name = serializers.CharField(source="programme.name", read_only=True)
    level_name     = serializers.CharField(source="level.name",      read_only=True)

    class Meta:
        model  = Student
        fields = (
            "id", "index_number", "full_name",
            "programme", "programme_name",
            "level", "level_name",
            "gender", "qr_code", "is_active", "created_at",
        )
        read_only_fields = ("id", "created_at")
        extra_kwargs     = {"qr_code": {"write_only": True}}


class StudentLookupSerializer(serializers.ModelSerializer):
    """Lightweight – returned during QR scan."""
    programme_name = serializers.CharField(source="programme.name", read_only=True)
    level_name     = serializers.CharField(source="level.name",      read_only=True)

    class Meta:
        model  = Student
        fields = ("id", "index_number", "full_name", "programme_name", "level_name", "gender", "is_active")


# ── Course ───────────────────────────────────────────────────────────────────

class CourseSerializer(serializers.ModelSerializer):
    programme_name = serializers.CharField(source="programme.name", read_only=True)
    level_name     = serializers.CharField(source="level.name",      read_only=True)

    class Meta:
        model  = Course
        fields = ("id", "course_code", "course_title", "programme", "programme_name", "level", "level_name")


# ── Exam Session ─────────────────────────────────────────────────────────────

class ExamSessionSerializer(serializers.ModelSerializer):
    course_code          = serializers.CharField(source="course.course_code",  read_only=True)
    course_title         = serializers.CharField(source="course.course_title", read_only=True)
    programme_name       = serializers.CharField(source="programme.name",       read_only=True)
    level_name           = serializers.CharField(source="level.name",           read_only=True)
    created_by_username  = serializers.CharField(source="created_by.username",  read_only=True)
    attendance_summary   = serializers.SerializerMethodField()

    class Meta:
        model  = ExamSession
        fields = (
            "id", "course", "course_code", "course_title",
            "programme", "programme_name", "level", "level_name",
            "date", "start_time", "end_time", "venue",
            "expected_students", "status",
            "created_by", "created_by_username", "created_at",
            "attendance_summary",
        )
        read_only_fields = ("id", "created_by", "created_at")

    def get_attendance_summary(self, obj):
        return obj.attendance_summary

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


# ── Attendance ───────────────────────────────────────────────────────────────

class AttendanceSerializer(serializers.ModelSerializer):
    student_name        = serializers.CharField(source="student.full_name",    read_only=True)
    index_number        = serializers.CharField(source="student.index_number", read_only=True)
    scanned_by_username = serializers.CharField(source="scanned_by.username",  read_only=True)
    section_display     = serializers.CharField(source="get_section_display",  read_only=True)
    status_display      = serializers.CharField(source="get_status_display",   read_only=True)

    class Meta:
        model  = ExamAttendance
        fields = (
            "id", "student", "student_name", "index_number",
            "exam_session", "section", "section_display",
            "scanned_by", "scanned_by_username",
            "scan_time", "status", "status_display", "remarks",
        )
        read_only_fields = ("id", "scanned_by", "scan_time", "status", "remarks")


# ── Scan ─────────────────────────────────────────────────────────────────────

class ScanSerializer(serializers.Serializer):
    qr_code      = serializers.CharField(max_length=255)
    exam_session = serializers.PrimaryKeyRelatedField(queryset=ExamSession.objects.all())
    section      = serializers.ChoiceField(choices=ExamAttendance.SECTION_CHOICES)

    def validate_exam_session(self, session):
        if session.status != "active":
            raise serializers.ValidationError("Exam session is not currently active.")
        return session

    def validate_qr_code(self, value):
        try:
            student = Student.objects.select_related("programme", "level").get(qr_code=value)
        except Student.DoesNotExist:
            raise serializers.ValidationError("Student not found for this QR code.")
        if not student.is_active:
            raise serializers.ValidationError("Student record is inactive.")
        self._student = student
        return value

    def save(self, **kwargs):
        student    = self._student
        session    = self.validated_data["exam_session"]
        section    = self.validated_data["section"]
        scanned_by = self.context["request"].user

        existing = ExamAttendance.objects.filter(
            student=student, exam_session=session, section=section
        ).first()

        if existing:
            return {
                "status":          "duplicate",
                "message":         f"Student already scanned for Section {section}.",
                "student":         StudentLookupSerializer(student).data,
                "attendance":      AttendanceSerializer(existing).data,
                "first_scan_time": existing.scan_time,
            }

        attendance = ExamAttendance.objects.create(
            student=student,
            exam_session=session,
            section=section,
            scanned_by=scanned_by,
            status="present",
        )

        return {
            "status":     "success",
            "message":    "Attendance recorded.",
            "student":    StudentLookupSerializer(student).data,
            "attendance": AttendanceSerializer(attendance).data,
        }
