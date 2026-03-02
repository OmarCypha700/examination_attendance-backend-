import csv
import io
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from .models import Program, Level, Student, Course, ExamSession, ExamAttendance
from .serializers import (
    ProgramSerializer, LevelSerializer, StudentSerializer,
    CourseSerializer, ExamSessionSerializer,
    AttendanceSerializer, ScanSerializer,
)
from accounts.permissions import IsAdmin, IsAdminOrReadOnly, CanScan


# ── Programs & Levels ────────────────────────────────────────────────────────

class ProgramListCreateView(generics.ListCreateAPIView):
    queryset          = Program.objects.all()
    serializer_class  = ProgramSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends   = (filters.SearchFilter,)
    search_fields     = ("name", "code")
    pagination_class  = None


class ProgramDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset          = Program.objects.all()
    serializer_class  = ProgramSerializer
    permission_classes = (IsAdminOrReadOnly,)


class LevelListCreateView(generics.ListCreateAPIView):
    queryset          = Level.objects.all()
    serializer_class  = LevelSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class  = None


class LevelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset          = Level.objects.all()
    serializer_class  = LevelSerializer
    permission_classes = (IsAdminOrReadOnly,)


# ── Students ─────────────────────────────────────────────────────────────────

class StudentListCreateView(generics.ListCreateAPIView):
    serializer_class  = StudentSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends   = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields  = ("programme", "level", "gender", "is_active")
    search_fields     = ("index_number", "full_name")

    def get_queryset(self):
        return Student.objects.select_related("programme", "level").all()


class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class  = StudentSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        return Student.objects.select_related("programme", "level").all()


class StudentBulkCreateView(APIView):
    permission_classes = (IsAdmin,)

    def post(self, request):
        items = request.data
        if not isinstance(items, list):
            return Response({"detail": "Expected a list."}, status=400)

        created_count, errors = 0, []
        students_to_create = []

        for i, item in enumerate(items):
            serializer = StudentSerializer(data=item)
            if serializer.is_valid():
                students_to_create.append(Student(**serializer.validated_data))
            else:
                errors.append({"row": i + 1, "errors": serializer.errors})

        if students_to_create:
            created_students = Student.objects.bulk_create(
                students_to_create, ignore_conflicts=True
            )
            created_count = len(created_students)

        return Response(
            {"created": created_count, "errors": errors},
            status=status.HTTP_207_MULTI_STATUS if errors else status.HTTP_201_CREATED,
        )


# ── Courses ──────────────────────────────────────────────────────────────────

class CourseListCreateView(generics.ListCreateAPIView):
    serializer_class  = CourseSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends   = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields  = ("programme", "level")
    search_fields     = ("course_code", "course_title")

    def get_queryset(self):
        return Course.objects.select_related("programme", "level").all()


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class  = CourseSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        return Course.objects.select_related("programme", "level").all()


# ── Exam Sessions ─────────────────────────────────────────────────────────────

class ExamSessionListCreateView(generics.ListCreateAPIView):
    serializer_class  = ExamSessionSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends   = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields  = ("status", "programme", "level", "date")
    search_fields     = ("course__course_code", "course__course_title", "venue")
    ordering_fields   = ("date", "start_time", "created_at")

    def get_queryset(self):
        return ExamSession.objects.select_related(
            "course", "programme", "level", "created_by"
        ).annotate(attendance_count=Count("attendances")).all()

    def get_permissions(self):
        return [IsAdmin()] if self.request.method == "POST" else [IsAuthenticated()]


class ExamSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class  = ExamSessionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ExamSession.objects.select_related(
            "course", "programme", "level", "created_by"
        ).all()

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return [IsAuthenticated()]


class ExamSessionStatusView(APIView):
    """PATCH /api/exam-sessions/<pk>/status/"""
    permission_classes = (IsAdmin,)

    def patch(self, request, pk):
        session    = get_object_or_404(ExamSession, pk=pk)
        new_status = request.data.get("status")

        if new_status not in ("scheduled", "active", "closed"):
            return Response({"detail": "Invalid status."}, status=400)

        if new_status == "active":
            conflict = ExamSession.objects.filter(
                programme=session.programme,
                level=session.level,
                status="active",
            ).exclude(pk=pk).first()
            if conflict:
                return Response(
                    {"detail": f"Session '{conflict}' is already active for this programme/level."},
                    status=400,
                )

        session.status = new_status
        session.save(update_fields=["status"])
        return Response(ExamSessionSerializer(session, context={"request": request}).data)


# ── QR Scan ──────────────────────────────────────────────────────────────────

class ScanView(APIView):
    permission_classes = (CanScan,)

    def post(self, request):
        serializer = ScanSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        http_status = (
            status.HTTP_200_OK if result["status"] == "duplicate"
            else status.HTTP_201_CREATED
        )
        return Response(result, status=http_status)


# ── Attendance Register ───────────────────────────────────────────────────────

class AttendanceListView(generics.ListAPIView):
    """GET /api/exam-sessions/<session_pk>/attendance/"""
    serializer_class  = AttendanceSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends   = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields  = ("section", "status")
    search_fields     = ("student__index_number", "student__full_name")

    def get_queryset(self):
        return (
            ExamAttendance.objects
            .filter(exam_session_id=self.kwargs["session_pk"])
            .select_related("student", "student__programme", "student__level", "scanned_by")
            .order_by("section", "scan_time")
        )


# ── Export ────────────────────────────────────────────────────────────────────

class AttendanceExportView(APIView):
    """GET /api/exam-sessions/<session_pk>/export/?format=csv|xlsx"""
    permission_classes = (IsAuthenticated,)

    def get(self, request, session_pk):
        session = get_object_or_404(
            ExamSession.objects.select_related("course", "programme", "level"),
            pk=session_pk,
        )
        export_format  = request.query_params.get("format", "xlsx").lower()
        section_filter = request.query_params.get("section")

        qs = (
            ExamAttendance.objects
            .filter(exam_session=session)
            .select_related("student", "student__programme", "student__level", "scanned_by")
            .order_by("section", "scan_time")
        )
        if section_filter in ("A", "B"):
            qs = qs.filter(section=section_filter)

        if export_format == "csv":
            return self._csv_response(session, qs)
        return self._xlsx_response(session, qs)

    def _csv_response(self, session, qs):
        filename = f"attendance_{session.course.course_code}_{session.date}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            "Section", "Index Number", "Full Name", "Programme",
            "Level", "Gender", "Scan Time", "Status", "Scanned By",
        ])
        for record in qs:
            s = record.student
            writer.writerow([
                record.get_section_display(),
                s.index_number, s.full_name,
                s.programme.name, s.level.name, s.gender,
                record.scan_time.strftime("%Y-%m-%d %H:%M:%S"),
                record.get_status_display(),
                record.scanned_by.username,
            ])
        return response

    def _xlsx_response(self, session, qs):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Attendance Register"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1E3A5F")
        center      = Alignment(horizontal="center")

        ws.merge_cells("A1:I1")
        ws["A1"] = "EXAMINATION ATTENDANCE REGISTER"
        ws["A1"].font      = Font(bold=True, size=14)
        ws["A1"].alignment = center

        ws.merge_cells("A2:I2")
        ws["A2"] = (
            f"{session.course.course_code} – {session.course.course_title} "
            f"| {session.programme.name} | {session.level.name}"
        )
        ws["A2"].alignment = center

        ws.merge_cells("A3:I3")
        venue     = session.venue or "—"
        end_time  = session.end_time.strftime("%H:%M") if session.end_time else "—"
        ws["A3"] = f"Date: {session.date}  |  Venue: {venue}  |  {session.start_time.strftime('%H:%M')} – {end_time}"
        ws["A3"].alignment = center

        ws.append([])

        headers = ["Section", "Index Number", "Full Name", "Programme", "Level", "Gender", "Scan Time", "Status", "Scanned By"]
        ws.append(headers)
        for cell in ws[5]:
            cell.font      = header_font
            cell.fill      = header_fill
            cell.alignment = center

        for record in qs:
            s = record.student
            ws.append([
                record.get_section_display(),
                s.index_number, s.full_name,
                s.programme.name, s.level.name, s.gender,
                record.scan_time.strftime("%Y-%m-%d %H:%M:%S"),
                record.get_status_display(),
                record.scanned_by.username,
            ])

        col_widths = [18, 16, 30, 25, 12, 8, 22, 12, 16]
        for i, width in enumerate(col_widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"attendance_{session.course.course_code}_{session.date}.xlsx"
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ── Dashboard ─────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    today = timezone.now().date()
    data = {
        "total_students":    Student.objects.filter(is_active=True).count(),
        "total_sessions":    ExamSession.objects.count(),
        "active_sessions":   ExamSession.objects.filter(status="active").count(),
        "total_scans_today": ExamAttendance.objects.filter(scan_time__date=today).count(),
    }
    return Response(data)
