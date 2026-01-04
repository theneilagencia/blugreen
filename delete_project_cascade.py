#!/usr/bin/env python3
"""Script para deletar projeto com CASCADE - remove todos os vínculos"""

import sys
from sqlmodel import Session, create_engine, text

# Database URL
DATABASE_URL = "postgresql://blugreen_user:blugreen_password@postgres:5432/blugreen_db"

def delete_project_cascade(project_id: int):
    """Delete project and all related data"""
    engine = create_engine(DATABASE_URL)
    
    with Session(engine) as session:
        try:
            print(f"Deletando projeto {project_id} e todos os vínculos...")
            
            # Delete workflows
            result = session.exec(text(f"DELETE FROM workflow WHERE project_id = {project_id}"))
            print(f"  - Workflows deletados: {result.rowcount}")
            
            # Delete tasks
            result = session.exec(text(f"DELETE FROM task WHERE project_id = {project_id}"))
            print(f"  - Tasks deletados: {result.rowcount}")
            
            # Delete project
            result = session.exec(text(f"DELETE FROM project WHERE id = {project_id}"))
            print(f"  - Projeto deletado: {result.rowcount}")
            
            session.commit()
            print(f"✅ Projeto {project_id} deletado com sucesso!")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"❌ Erro ao deletar projeto {project_id}: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python delete_project_cascade.py <project_id>")
        sys.exit(1)
    
    project_id = int(sys.argv[1])
    success = delete_project_cascade(project_id)
    sys.exit(0 if success else 1)
