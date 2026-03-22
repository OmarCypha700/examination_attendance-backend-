from django.urls import path

from . import views

urlpatterns = [
    # ── Reference ────────────
    path("programs/", views.ProgramListCreateView.as_view(), name="program-list"),
    path(
        "programs/<int:pk>/", views.ProgramDetailView.as_view(), name="program-detail"
    ),
    path("levels/", views.LevelListCreateView.as_view(), name="level-list"),
    path("levels/<int:pk>/", views.LevelDetailView.as_view(), name="level-detail"),
    # ── Students ───────────
    path("students/export/", views.StudentExportView.as_view(), name="student-export"),
    path("students/import/", views.StudentImportView.as_view(), name="student-import"),
    path("students/bulk/", views.StudentBulkCreateView.as_view(), name="student-bulk"),
    path("students/", views.StudentListCreateView.as_view(), name="student-list"),
    path(
        "students/<int:pk>/", views.StudentDetailView.as_view(), name="student-detail"
    ),
    # ── Courses ────────────
    path("courses/", views.CourseListCreateView.as_view(), name="course-list"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="course-detail"),
    path("courses/export/", views.CourseExportView.as_view(), name="course-export"),
    path("courses/import/", views.CourseImportView.as_view(), name="course-import"),
    path(
        "courses/template/", views.CourseTemplateView.as_view(), name="course-template"
    ),
    # ── Exam Sessions ──────
    path(
        "exam-sessions/", views.ExamSessionListCreateView.as_view(), name="session-list"
    ),
    path(
        "exam-sessions/export/",
        views.SessionExportView.as_view(),
        name="session-export",
    ),
    path(
        "exam-sessions/import/",
        views.SessionImportView.as_view(),
        name="session-import",
    ),
    path(
        "exam-sessions/<int:pk>/",
        views.ExamSessionDetailView.as_view(),
        name="session-detail",
    ),
    path(
        "exam-sessions/<int:pk>/status/",
        views.ExamSessionStatusView.as_view(),
        name="session-status",
    ),
    path(
        "exam-sessions/<int:session_pk>/attendance/",
        views.AttendanceListView.as_view(),
        name="attendance-list",
    ),
    path(
        "exam-sessions/<int:session_pk>/export/",
        views.AttendanceExportView.as_view(),
        name="attendance-export",
    ),
    # ── Staff Users ────────
    path("staff/export/", views.StaffExportView.as_view(), name="staff-export"),
    path("staff/import/", views.StaffImportView.as_view(), name="staff-import"),
    # ── Scan ───────────────
    path("scan/", views.ScanView.as_view(), name="scan"),
    # ── Dashboard ──────────
    path("dashboard/", views.dashboard, name="dashboard"),
]
