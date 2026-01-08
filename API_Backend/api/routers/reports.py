"""
API endpoints for report generation
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io
import tempfile
import os

from api import schemas, models, auth
from api.database import get_db
from core.report_generator import ReportGenerator

router = APIRouter()

@router.post("/generate", response_model=schemas.APIResponse)
async def generate_report(
    request: schemas.ReportGenerateRequest,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Generate a report for an analysis
    """
    try:
        # Get analysis
        analysis = db.query(models.Analysis)\
            .filter(models.Analysis.id == request.analysis_id)\
            .first()
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found"
            )
        
        # Check authorization
        if current_user and analysis.user_id and analysis.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to generate report for this analysis"
            )
        
        # Generate report
        generator = ReportGenerator()
        
        if request.format == schemas.ReportFormat.MARKDOWN:
            report_content = generator.generate_markdown_report(
                analysis.metrics or {},
                analysis.risk_results or {},
                analysis.score_result or {},
                analysis.ai_explanations or {}
            )
            
            # Save to database
            report = models.Report(
                analysis_id=analysis.id,
                report_type="markdown",
                content=report_content
            )
            
        elif request.format == schemas.ReportFormat.HTML:
            markdown_report = generator.generate_markdown_report(
                analysis.metrics or {},
                analysis.risk_results or {},
                analysis.score_result or {},
                analysis.ai_explanations or {}
            )
            report_content = generator.generate_html_report(markdown_report)
            
            # Save to database
            report = models.Report(
                analysis_id=analysis.id,
                report_type="html",
                content=report_content
            )
            
        elif request.format == schemas.ReportFormat.PDF:
            # PDF generation (requires additional libraries like weasyprint or reportlab)
            # For now, return markdown
            report_content = generator.generate_markdown_report(
                analysis.metrics or {},
                analysis.risk_results or {},
                analysis.score_result or {},
                analysis.ai_explanations or {}
            )
            
            report = models.Report(
                analysis_id=analysis.id,
                report_type="pdf",
                content="PDF generation coming soon. Here's markdown version:\n\n" + report_content
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported report format"
            )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        response_data = schemas.ReportResponse(
            id=report.id,
            analysis_id=report.analysis_id,
            report_type=report.report_type,
            content=report.content if len(report.content or "") < 10000 else report.content[:10000] + "...",
            download_url=f"/api/reports/download/{report.id}",
            generated_at=report.generated_at
        )
        
        return schemas.APIResponse.success_response(
            data=response_data,
            message="Report generated successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report: {str(e)}"
        )

@router.get("/download/{report_id}")
async def download_report(
    report_id: str,
    format: Optional[str] = None,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Download a generated report
    """
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )
    
    # Get associated analysis for authorization check
    analysis = db.query(models.Analysis)\
        .filter(models.Analysis.id == report.analysis_id)\
        .first()
    
    if current_user and analysis.user_id and analysis.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to download this report"
        )
    
    # Update download count
    report.download_count = (report.download_count or 0) + 1
    db.commit()
    
    # Return appropriate response
    if format == "file" and report.content:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=f".{report.report_type}") as f:
            f.write(report.content)
            temp_path = f.name
        
        try:
            return FileResponse(
                temp_path,
                filename=f"tradeguard_report_{report.id}.{report.report_type}",
                media_type="text/plain" if report.report_type == "markdown" else "text/html"
            )
        finally:
            # Clean up temp file after sending
            os.unlink(temp_path)
    
    else:
        # Return as JSON with content
        return {
            "id": report.id,
            "analysis_id": report.analysis_id,
            "report_type": report.report_type,
            "content": report.content,
            "download_count": report.download_count,
            "generated_at": report.generated_at
        }

@router.get("/{analysis_id}", response_model=schemas.APIResponse)
async def list_reports(
    analysis_id: str,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: Session = Depends(get_db)
):
    """
    List all reports for an analysis
    """
    analysis = db.query(models.Analysis)\
        .filter(models.Analysis.id == analysis_id)\
        .first()
    
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found"
        )
    
    if current_user and analysis.user_id and analysis.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view reports for this analysis"
        )
    
    reports = db.query(models.Report)\
        .filter(models.Report.analysis_id == analysis_id)\
        .order_by(models.Report.generated_at.desc())\
        .all()
    
    response_data = [
        {
            "id": r.id,
            "report_type": r.report_type,
            "download_count": r.download_count,
            "generated_at": r.generated_at,
            "download_url": f"/api/reports/download/{r.id}"
        }
        for r in reports
    ]
    
    return schemas.APIResponse.success_response(data=response_data)