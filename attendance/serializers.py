from rest_framework import serializers

from .models import (Course, ExamAttendance, ExamSession, Level, Program,
                     Student)

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
            "is_active", "created_at",
        )
        read_only_fields = ("id", "created_at")

class StudentLookupSerializer(serializers.ModelSerializer):
    """Lightweight – returned during QR scan."""
    programme_name = serializers.CharField(source="programme.name", read_only=True)
    level_name     = serializers.CharField(source="level.name",      read_only=True)

    class Meta:
        model  = Student
        fields = ("id", "index_number", "full_name", "programme_name", "level_name", "is_active")

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
    programme_name       = serializers.CharField(source="programme.code",       read_only=True)
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
    student_name         = serializers.CharField(source="student.full_name",    read_only=True)
    index_number         = serializers.CharField(source="student.index_number", read_only=True)
    student_programme_name = serializers.CharField(source="student.programme.name", read_only=True)
    scanned_by_username  = serializers.CharField(source="scanned_by.username",  read_only=True)
    section_display      = serializers.CharField(source="get_section_display",  read_only=True)
    status_display       = serializers.CharField(source="get_status_display",   read_only=True)

    class Meta:
        model  = ExamAttendance
        fields = (
            "id", "student", "student_name", "index_number",
            "student_programme_name", "exam_session", "section", 
            "section_display", "scanned_by", "scanned_by_username",
            "scan_time", "status", "status_display", "remarks",
        )
        read_only_fields = ("id", "scanned_by", "scan_time", "status", "remarks")

# ── Scan ─────────────────────────────────────────────────────────────────────
class ScanSerializer(serializers.Serializer):
    """
    The frontend generates a QR code containing only the student's index_number.
    The scanned value is sent here as `index_number` for lookup and attendance recording.
    """

    index_number = serializers.CharField(max_length=50)

    exam_session = serializers.PrimaryKeyRelatedField(
        queryset=ExamSession.objects.filter(status="active")
    )

    section = serializers.ChoiceField(
        choices=ExamAttendance.SECTION_CHOICES
    )


    def validate_exam_session(self, session):
        if session.status != "active":
            raise serializers.ValidationError(
                "Exam session is not currently active."
            )
        return session


    def validate_index_number(self, value):

        try:
            student = Student.objects.select_related(
                "programme", "level"
            ).get(index_number=value.strip())

        except Student.DoesNotExist:
            raise serializers.ValidationError(
                "No student found with this index number."
            )

        if not student.is_active:
            raise serializers.ValidationError(
                "This student's record is inactive."
            )

        self._student = student
        return value


    def validate(self, attrs):

        index_number = attrs["index_number"].strip()
        session = attrs["exam_session"]

        try:
            student = Student.objects.only(
                "id", "programme_id", "level_id", "is_active"
            ).get(index_number=index_number)

        except Student.DoesNotExist:
            raise serializers.ValidationError(
                {"index_number": "No student found."}
            )

        if not student.is_active:
            raise serializers.ValidationError(
                {"index_number": "Student is inactive."}
            )

        if student.programme_id != session.programme_id:
            raise serializers.ValidationError(
                {"index_number": "Student not in this programme."}
            )

        if student.level_id != session.level_id:
            raise serializers.ValidationError(
                {"index_number": "Student not in this level."}
            )

        attrs["student"] = student
        return attrs


    def save(self, **kwargs):

        # student = self._student
        student = self.validated_data["student"]
        session = self.validated_data["exam_session"]
        section = self.validated_data["section"]
        scanned_by = self.context["request"].user

        attendance, created = ExamAttendance.objects.get_or_create(
            student=student,
            exam_session=session,
            section=section,
            defaults={
                "scanned_by": scanned_by,
                "status": "present"
            }
        )

        if not created:
            return {
                "status": "duplicate",
                "message": f"Student already scanned for Section {section}.",
                "student": StudentLookupSerializer(student).data,
                "attendance": AttendanceSerializer(attendance).data,
                "first_scan_time": attendance.scan_time,
            }

        return {
            "status": "success",
            "message": "Attendance recorded.",
            "student": StudentLookupSerializer(student).data,
            "attendance": AttendanceSerializer(attendance).data,
        }