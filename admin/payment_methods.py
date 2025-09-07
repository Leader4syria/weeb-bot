from flask import render_template, request, redirect, url_for, flash
from . import admin_bp, admin_required
from database import Session, PaymentMethod
import traceback

@admin_bp.route('/payment-methods', endpoint='admin_payment_methods')
@admin_required
def admin_payment_methods():
    try:
        s = Session()
        payment_methods = s.query(PaymentMethod).order_by(PaymentMethod.id).all()
        s.close()
        return render_template('payment_methods.html', payment_methods=payment_methods)
    except Exception as e:
        print(f"خطأ في admin_payment_methods: {e}\n{traceback.format_exc()}")
        flash("حدث خطأ غير متوقع أثناء تحميل صفحة طرق الدفع.", "error")
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/payment-methods/add', methods=['POST'], endpoint='admin_add_payment_method')
@admin_required
def admin_add_payment_method():
    try:
        name = request.form.get('name')
        description = request.form.get('description')
        contact_user = request.form.get('contact_user')
        instructions = request.form.get('instructions')
        is_available = 'is_available' in request.form

        if not name:
            flash('اسم طريقة الدفع مطلوب.', 'error')
            return redirect(url_for('admin.admin_payment_methods'))

        s = Session()
        try:
            new_method = PaymentMethod(
                name=name,
                description=description,
                contact_user=contact_user,
                instructions=instructions,
                is_available=is_available
            )
            s.add(new_method)
            s.commit()
            flash(f'تمت إضافة طريقة الدفع "{name}" بنجاح.', 'success')
        except Exception as e:
            s.rollback()
            flash(f'حدث خطأ أثناء إضافة طريقة الدفع: {e}', 'error')
        finally:
            s.close()
        return redirect(url_for('admin.admin_payment_methods'))
    except Exception as e:
        print(f"خطأ في admin_add_payment_method: {e}\n{traceback.format_exc()}")
        flash("حدث خطأ غير متوقع أثناء إضافة طريقة الدفع.", "error")
        return redirect(url_for('admin.admin_payment_methods'))

@admin_bp.route('/payment-methods/edit/<int:method_id>', methods=['POST'], endpoint='admin_edit_payment_method')
@admin_required
def admin_edit_payment_method(method_id):
    name = request.form.get('name')
    description = request.form.get('description')
    contact_user = request.form.get('contact_user')
    instructions = request.form.get('instructions')
    is_available = 'is_available' in request.form

    if not name:
        flash('اسم طريقة الدفع مطلوب.', 'error')
        return redirect(url_for('admin.admin_payment_methods'))

    s = Session()
    method = s.query(PaymentMethod).get(method_id)

    if not method:
        flash('طريقة الدفع غير موجودة.', 'error')
        s.close()
        return redirect(url_for('admin.admin_payment_methods'))

    try:
        method.name = name
        method.description = description
        method.contact_user = contact_user
        method.instructions = instructions
        method.is_available = is_available
        s.commit()
        flash(f'تم تحديث طريقة الدفع "{name}" بنجاح.', 'success')
    except Exception as e:
        s.rollback()
        flash(f'حدث خطأ أثناء تحديث طريقة الدفع: {e}', 'error')
    finally:
        s.close()

    return redirect(url_for('admin.admin_payment_methods'))

@admin_bp.route('/payment-methods/delete/<int:method_id>', methods=['POST'], endpoint='admin_delete_payment_method')
@admin_required
def admin_delete_payment_method(method_id):
    try:
        s = Session()
        method = s.query(PaymentMethod).get(method_id)

        if not method:
            flash('طريقة الدفع غير موجودة.', 'error')
            s.close()
            return redirect(url_for('admin.admin_payment_methods'))

        try:
            s.delete(method)
            s.commit()
            flash(f'تم حذف طريقة الدفع "{method.name}" بنجاح.', 'success')
        except Exception as e:
            s.rollback()
            flash(f'حدث خطأ أثناء حذف طريقة الدفع: {e}', 'error')
        finally:
            s.close()
        return redirect(url_for('admin.admin_payment_methods'))
    except Exception as e:
        print(f"خطأ في admin_delete_payment_method: {e}\n{traceback.format_exc()}")
        flash("حدث خطأ غير متوقع أثناء حذف طريقة الدفع.", "error")
        return redirect(url_for('admin.admin_payment_methods'))
